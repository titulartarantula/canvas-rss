"""Parser and scraper for the Canvas Feature Option Summary canonical page.

Parses the Instructure Community KB article that lists all Canvas feature
options and previews with their configuration states, descriptions, and
documentation links.

Source: https://community.instructure.com/en/kb/articles/531316-unknown
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from src.utils.database import Database

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    PlaywrightTimeout = Exception

logger = logging.getLogger("canvas_rss")

# Canonical page URL
CANONICAL_PAGE_URL = (
    "https://community.instructure.com/en/kb/articles/531316-unknown"
)

# Section heading text -> lifecycle_stage mapping
SECTION_LIFECYCLE_MAP: Dict[str, str] = {
    "Pending Feature Options": "optional",
    "Optional Features": "optional",
    "Default Optional Features": "optional",
    "Feature Previews": "feature_preview",
}

# Sections where options will eventually be enforced by Canvas
ENFORCEMENT_SECTIONS = {"Pending Feature Options"}


@dataclass
class CanonicalOption:
    """A feature option parsed from the canonical page."""

    name: str
    description: str
    lifecycle_stage: str  # 'feature_preview' | 'optional'
    will_be_enforced: bool = False
    prod_account_state: str = "N/A"
    prod_course_state: str = "N/A"
    beta_account_state: str = "N/A"
    beta_course_state: str = "N/A"
    doc_url: Optional[str] = None
    user_group_url: Optional[str] = None


@dataclass
class ConfigParseResult:
    """Result of parsing a configuration text string."""

    prod_account_state: str = "N/A"
    prod_course_state: str = "N/A"
    beta_account_state: str = "N/A"
    beta_course_state: str = "N/A"


def _parse_state_tuple(state_text: str) -> Tuple[str, str]:
    """Parse a parenthetical state like '(Disabled/Unlocked)' into (enabled_state, lock_state).

    Returns a tuple of (state_value, lock_value) where:
    - state_value is 'enabled' or 'disabled'
    - lock_value is 'locked' or 'unlocked' or '' (empty if no lock specified)
    """
    # Extract content inside parentheses
    match = re.search(r"\(([^)]+)\)", state_text)
    if not match:
        return ("", "")

    inner = match.group(1).strip()
    parts = [p.strip().lower() for p in inner.split("/")]

    if len(parts) == 2:
        # e.g., "Disabled/Unlocked" or "Enabled/Locked"
        return (parts[0], parts[1])
    elif len(parts) == 1:
        # e.g., "Disabled" or "Enabled" - no lock concept
        return (parts[0], "")
    return ("", "")


def _build_account_state(enabled: str, lock: str) -> str:
    """Build the account state string from enabled/lock components.

    Args:
        enabled: 'enabled' or 'disabled'
        lock: 'locked', 'unlocked', or '' (no lock concept)
    """
    if not enabled:
        return "N/A"
    if lock:
        return f"{enabled}_{lock}"
    # No lock concept - account-only feature
    return enabled


def _build_course_state(enabled: str) -> str:
    """Build the course state string. Course level has NO lock concept."""
    if not enabled:
        return "N/A"
    return enabled


def _parse_single_config_line(line: str) -> ConfigParseResult:
    """Parse a single configuration line (no Beta:/Production: prefix, no semicolons).

    Handles formats like:
    - "Account (Disabled/Unlocked)"
    - "Account/Course (Disabled/Unlocked)"
    - "Account (Disabled)"
    - "Course (Disabled)"
    - "(Disabled/Unlocked)" - no level prefix
    - "Must be configured by a Customer Success Manager (CSM)"
    - "LTI Configuration Required"
    - "User Settings (Disabled)"
    - "Enabled by default"
    """
    line = line.strip()
    result = ConfigParseResult()

    if not line:
        return result

    # Special cases first
    lower = line.lower()

    if "customer success manager" in lower or "csm" in lower:
        result.prod_account_state = "csm_managed"
        return result

    if "lti configuration required" in lower:
        result.prod_account_state = "lti_required"
        return result

    if "user settings" in lower or "user setting" in lower:
        result.prod_account_state = "user_setting"
        return result

    if lower == "enabled by default":
        result.prod_account_state = "enabled_unlocked"
        return result

    # Parse level prefix and state
    enabled, lock = _parse_state_tuple(line)

    if "account/course" in lower or "account / course" in lower:
        # Both account and course level
        result.prod_account_state = _build_account_state(enabled, lock)
        # Course level: no lock concept, just enabled/disabled
        result.prod_course_state = _build_course_state(enabled)
        return result

    if re.match(r"^account\s*[\(]", lower) or lower.startswith("account "):
        # Account-level only
        result.prod_account_state = _build_account_state(enabled, lock)
        return result

    if lower.startswith("course"):
        # Course-level only
        result.prod_course_state = _build_course_state(enabled)
        return result

    # No level prefix but has state in parens - treat as account
    if enabled:
        result.prod_account_state = _build_account_state(enabled, lock)
        return result

    # Unrecognized format - log and return defaults
    logger.warning("Unrecognized config line format: %r", line)
    return result


def parse_config_text(config_text: str) -> ConfigParseResult:
    """Parse a configuration text string into the 4 state columns.

    The config_text comes from the Configuration column of the canonical page
    tables. It may contain multiple lines (from separate <p> elements),
    separated by newlines or semicolons.

    Handles:
    - Single-line: "Account (Disabled/Unlocked)"
    - Multi-line: "Account (Disabled/Locked)\\nCourse (Disabled)"
    - Semicolons: "Account (Disabled/Locked); Course (Disabled)"
    - Beta/Prod: "Beta: Account/Course (Enabled/Unlocked)\\nProduction: Account/Course (Disabled/Unlocked)"
    - Typo split: "Account\\n(Disabled/Unlocked)" -> rejoin as "Account (Disabled/Unlocked)"

    Args:
        config_text: The raw configuration text, possibly multi-line.

    Returns:
        ConfigParseResult with the 4 state columns populated.
    """
    if not config_text or not config_text.strip():
        return ConfigParseResult()

    text = config_text.strip()

    # Split on newlines and/or semicolons to get individual lines
    # First split on newlines, then on semicolons within each
    raw_lines = []
    for nl_part in text.split("\n"):
        for sc_part in nl_part.split(";"):
            stripped = sc_part.strip()
            if stripped:
                raw_lines.append(stripped)

    # Rejoin lines where a line starts with '(' and the previous doesn't end
    # with ')' - this handles the "Account\n(Disabled/Unlocked)" typo pattern
    lines: List[str] = []
    for line in raw_lines:
        if lines and line.startswith("(") and not lines[-1].endswith(")"):
            lines[-1] = lines[-1] + " " + line
        else:
            lines.append(line)

    # Check for Beta:/Production: prefixes
    has_beta = any(l.lower().startswith("beta:") for l in lines)
    has_prod = any(l.lower().startswith("production:") for l in lines)

    if has_beta or has_prod:
        return _parse_beta_prod_config(lines)

    # No beta/prod split - all lines are production config
    result = ConfigParseResult()
    for line in lines:
        line_result = _parse_single_config_line(line)
        # Merge: non-N/A values override N/A
        if line_result.prod_account_state != "N/A":
            result.prod_account_state = line_result.prod_account_state
        if line_result.prod_course_state != "N/A":
            result.prod_course_state = line_result.prod_course_state

    return result


def _parse_beta_prod_config(lines: List[str]) -> ConfigParseResult:
    """Parse config lines that have Beta: and/or Production: prefixes."""
    result = ConfigParseResult()

    for line in lines:
        lower = line.lower()

        if lower.startswith("beta:"):
            remainder = line[len("beta:"):].strip()
            line_result = _parse_single_config_line(remainder)
            result.beta_account_state = line_result.prod_account_state
            result.beta_course_state = line_result.prod_course_state

        elif lower.startswith("production:"):
            remainder = line[len("production:"):].strip()
            line_result = _parse_single_config_line(remainder)
            result.prod_account_state = line_result.prod_account_state
            result.prod_course_state = line_result.prod_course_state

        else:
            # Line without prefix in a beta/prod context - treat as production
            line_result = _parse_single_config_line(line)
            if line_result.prod_account_state != "N/A":
                result.prod_account_state = line_result.prod_account_state
            if line_result.prod_course_state != "N/A":
                result.prod_course_state = line_result.prod_course_state

    return result


def _extract_config_text_from_cell(td: Tag) -> str:
    """Extract configuration text from a table cell, preserving paragraph breaks.

    The real page uses <p> elements within config cells. We join them with
    newlines so parse_config_text can handle multi-line formats correctly.
    """
    paragraphs = td.find_all("p")
    if paragraphs:
        return "\n".join(p.get_text(strip=True) for p in paragraphs)
    return td.get_text(strip=True)


def _resolve_redirect_url(url: str) -> str:
    """Extract the actual target URL from Instructure's redirect wrapper.

    Instructure Community links go through a redirect like:
    https://community.instructure.com/home/leaving?allowTrusted=1&target=...

    This recursively decodes the target URL.
    """
    if not url:
        return url

    # Try to extract target= parameter from redirect URLs
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    if "leaving" in parsed.path:
        params = urllib.parse.parse_qs(parsed.query)
        target = params.get("target", [None])[0]
        if target:
            # Recursively resolve in case of double-wrapped redirects
            return _resolve_redirect_url(target)

    return url


def _find_table_after_heading(heading: Tag) -> Optional[Tag]:
    """Find the next table element after an H2 heading.

    The real page structure has H2 headings as direct children of .userContent,
    with tables wrapped in <div class="tableWrapper"> siblings. There may be
    intermediate elements (paragraphs, etc.) between the heading and the table.
    """
    sibling = heading.find_next_sibling()
    while sibling:
        # Check if this sibling contains a table
        if sibling.name == "table":
            return sibling
        if isinstance(sibling, Tag):
            table = sibling.find("table")
            if table:
                return table
            # Stop if we hit the next H2 (different section)
            if sibling.name == "h2":
                return None
        sibling = sibling.find_next_sibling()
    return None


def _parse_table_row(
    row: Tag,
    lifecycle_stage: str,
    section_heading: str,
    column_headers: List[str],
    will_be_enforced: bool = False,
) -> Optional[CanonicalOption]:
    """Parse a single table row into a CanonicalOption.

    Args:
        row: The <tr> element
        lifecycle_stage: The lifecycle stage for this section
        section_heading: The section heading text (for context)
        column_headers: The list of column header texts for this table

    Returns:
        CanonicalOption or None if the row couldn't be parsed
    """
    cells = row.find_all("td")
    if not cells:
        return None

    # Build a column name -> cell index map from headers
    col_map: Dict[str, int] = {}
    for i, header in enumerate(column_headers):
        header_lower = header.strip().lower()
        if "feature" in header_lower:
            col_map["name"] = i
        elif "summary" in header_lower:
            col_map["summary"] = i
        elif "configuration" in header_lower:
            col_map["config"] = i
        elif "release" in header_lower:
            col_map["release_notes"] = i
        elif "user group" in header_lower:
            col_map["user_group"] = i

    if "name" not in col_map or "summary" not in col_map:
        return None

    # Validate cell count
    if len(cells) < len(column_headers):
        logger.warning(
            "Row has %d cells but expected %d columns in '%s' section",
            len(cells),
            len(column_headers),
            section_heading,
        )
        # Still try to parse what we can

    # Extract name and doc_url from first cell
    name_cell = cells[col_map["name"]]
    name = name_cell.get_text(strip=True)
    if not name:
        return None

    doc_url = None
    name_link = name_cell.find("a")
    if name_link and name_link.get("href"):
        doc_url = _resolve_redirect_url(name_link["href"])

    # Extract description from summary cell
    summary_idx = col_map["summary"]
    description = cells[summary_idx].get_text(strip=True) if summary_idx < len(cells) else ""

    # Parse configuration
    config_result = ConfigParseResult()
    if "config" in col_map and col_map["config"] < len(cells):
        config_text = _extract_config_text_from_cell(cells[col_map["config"]])
        config_result = parse_config_text(config_text)
    elif section_heading == "Default Optional Features":
        # Default Optional Features have no Configuration column
        # These are enabled by default at account level, unlocked
        config_result.prod_account_state = "enabled_unlocked"

    # Extract user group URL
    user_group_url = None
    if "user_group" in col_map and col_map["user_group"] < len(cells):
        ug_cell = cells[col_map["user_group"]]
        ug_link = ug_cell.find("a")
        if ug_link and ug_link.get("href"):
            user_group_url = _resolve_redirect_url(ug_link["href"])

    return CanonicalOption(
        name=name,
        description=description,
        lifecycle_stage=lifecycle_stage,
        will_be_enforced=will_be_enforced,
        prod_account_state=config_result.prod_account_state,
        prod_course_state=config_result.prod_course_state,
        beta_account_state=config_result.beta_account_state,
        beta_course_state=config_result.beta_course_state,
        doc_url=doc_url,
        user_group_url=user_group_url,
    )


def parse_canonical_page_html(html: str) -> List[CanonicalOption]:
    """Parse the full Canvas Feature Option Summary page HTML.

    Finds H2 section headings, maps them to lifecycle stages, then parses
    the table following each heading to extract feature options.

    Args:
        html: The full HTML of the canonical page.

    Returns:
        List of CanonicalOption objects parsed from the page.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find the article content container
    content = soup.select_one(".userContent")
    if not content:
        # Fallback: try article tag or the whole body
        content = soup.find("article") or soup.find("body") or soup
        logger.warning(
            "Could not find .userContent container, using fallback: %s",
            content.name if hasattr(content, "name") else "soup",
        )

    options: List[CanonicalOption] = []

    # Find all H2 headings that match our section map
    for h2 in content.find_all("h2"):
        heading_text = h2.get_text(strip=True)
        lifecycle_stage = SECTION_LIFECYCLE_MAP.get(heading_text)
        if not lifecycle_stage:
            continue

        # Find the table that follows this heading
        table = _find_table_after_heading(h2)
        if not table:
            logger.warning(
                "No table found after heading '%s'", heading_text
            )
            continue

        # Get column headers from the first row (th elements)
        header_row = table.find("tr")
        if not header_row:
            continue
        column_headers = [
            th.get_text(strip=True) for th in header_row.find_all("th")
        ]
        if not column_headers:
            # Some tables might use td for headers
            column_headers = [
                td.get_text(strip=True) for td in header_row.find_all("td")
            ]

        # Parse data rows (skip header row)
        will_be_enforced = heading_text in ENFORCEMENT_SECTIONS
        rows = table.find_all("tr")[1:]
        for row in rows:
            option = _parse_table_row(
                row, lifecycle_stage, heading_text, column_headers,
                will_be_enforced=will_be_enforced,
            )
            if option:
                options.append(option)

    logger.info(
        "Parsed %d feature options from canonical page", len(options)
    )
    return options


def _slugify(name: str) -> str:
    """Convert a feature option name to a slug suitable for option_id.

    Args:
        name: Feature name (e.g., "Document Processor").

    Returns:
        Slugified text (e.g., "document_processor").
    """
    if not name:
        return ""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug[:80]  # Limit length


def _match_feature_id(name: str) -> str:
    """Match a canonical option name to a CANVAS_FEATURES feature_id.

    Uses keyword matching against the canonical CANVAS_FEATURES dictionary
    to find the best matching feature category.

    Args:
        name: Feature option name from the canonical page.

    Returns:
        Best matching feature_id, or 'general' if no match.
    """
    from src.constants import CANVAS_FEATURES

    name_lower = name.lower()

    # Direct name matches against feature names/ids
    for feature_id, feature_name in CANVAS_FEATURES.items():
        if feature_name.lower() in name_lower or feature_id in name_lower:
            return feature_id

    # Keyword-based fallbacks
    if 'quiz' in name_lower:
        return 'new_quizzes' if 'new' in name_lower else 'classic_quizzes'
    if 'grade' in name_lower or 'speedgrader' in name_lower:
        return 'gradebook'
    if 'assignment' in name_lower:
        return 'assignments'
    if 'discussion' in name_lower:
        return 'discussions'
    if 'module' in name_lower:
        return 'modules'
    if 'page' in name_lower:
        return 'pages'
    if 'rubric' in name_lower:
        return 'rubrics'
    if 'calendar' in name_lower:
        return 'calendar'
    if 'inbox' in name_lower or 'conversation' in name_lower:
        return 'inbox'
    if 'studio' in name_lower:
        return 'canvas_studio'
    if 'mobile' in name_lower:
        return 'canvas_mobile'
    if 'api' in name_lower:
        return 'api'
    if 'lti' in name_lower or 'external' in name_lower:
        return 'external_apps_lti'
    if 'rce' in name_lower or 'rich content' in name_lower:
        return 'rich_content_editor'
    if 'outcome' in name_lower or 'mastery' in name_lower:
        return 'outcomes'
    if 'announcement' in name_lower:
        return 'announcements'
    if 'portfolio' in name_lower or 'eportfolio' in name_lower:
        return 'eportfolios'
    if 'analytic' in name_lower:
        return 'canvas_analytics'
    if 'elementary' in name_lower:
        return 'canvas_elementary'
    if 'blueprint' in name_lower:
        return 'blueprint_courses'
    if 'conference' in name_lower:
        return 'conferences'
    if 'collaborat' in name_lower:
        return 'collaborations'
    if 'navigation' in name_lower:
        return 'global_navigation'
    if 'notification' in name_lower:
        return 'notifications'
    if 'file' in name_lower:
        return 'files'
    if 'course pacing' in name_lower:
        return 'courses'

    return 'general'


def scrape_canonical_options(db: "Database") -> List[CanonicalOption]:
    """Scrape the canonical feature options page and upsert into database.

    Uses Playwright to fetch the Canvas Feature Option Summary page, parses
    the HTML, and upserts each option into the database with source='canonical_page'.

    Args:
        db: Database instance (src.utils.database.Database).

    Returns:
        List of parsed CanonicalOption entries.
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning(
            "Playwright is not installed. Canonical options scraping will be disabled. "
            "Install with: pip install playwright && playwright install chromium"
        )
        return []

    logger.info("Fetching canonical feature options page: %s", CANONICAL_PAGE_URL)

    pw = None
    browser = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        # Navigate with generous timeout for community page
        page.goto(CANONICAL_PAGE_URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for the content to be available
        try:
            page.wait_for_selector(".userContent", timeout=15000)
        except Exception:
            logger.warning("Could not find .userContent selector, proceeding with current page content")

        html = page.content()

    except PlaywrightTimeout:
        logger.error("Timeout while fetching canonical options page: %s", CANONICAL_PAGE_URL)
        return []
    except Exception as e:
        logger.error("Error fetching canonical options page: %s", e)
        return []
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if pw:
            try:
                pw.stop()
            except Exception:
                pass

    # Parse the HTML
    options = parse_canonical_page_html(html)

    if not options:
        logger.warning("No feature options parsed from canonical page")
        return []

    # Upsert each option into the database
    # Track seen slugs to merge duplicates (e.g., "New Quizzes" appears
    # in both Pending and Feature Previews sections — merge will_be_enforced)
    seen_slugs: Dict[str, CanonicalOption] = {}
    upserted = 0
    for option in options:
        option_id = _slugify(option.name)
        if not option_id:
            logger.warning("Could not generate option_id for: %r", option.name)
            continue

        if option_id in seen_slugs:
            # Merge: carry forward will_be_enforced from earlier occurrence,
            # prefer feature_preview lifecycle over optional (more specific)
            prev = seen_slugs[option_id]
            merged_enforced = option.will_be_enforced or prev.will_be_enforced
            merged_stage = 'feature_preview' if option.lifecycle_stage == 'feature_preview' or prev.lifecycle_stage == 'feature_preview' else option.lifecycle_stage
            logger.info(
                "Merging duplicate '%s': lifecycle=%s, will_be_enforced=%s",
                option.name, merged_stage, merged_enforced,
            )
            option = CanonicalOption(
                name=option.name,
                description=option.description or prev.description,
                lifecycle_stage=merged_stage,
                will_be_enforced=merged_enforced,
                prod_account_state=option.prod_account_state if option.prod_account_state != 'N/A' else prev.prod_account_state,
                prod_course_state=option.prod_course_state if option.prod_course_state != 'N/A' else prev.prod_course_state,
                beta_account_state=option.beta_account_state if option.beta_account_state != 'N/A' else prev.beta_account_state,
                beta_course_state=option.beta_course_state if option.beta_course_state != 'N/A' else prev.beta_course_state,
                doc_url=option.doc_url or prev.doc_url,
                user_group_url=option.user_group_url or prev.user_group_url,
            )
        seen_slugs[option_id] = option

        feature_id = _match_feature_id(option.name)

        try:
            db.upsert_feature_option(
                option_id=option_id,
                feature_id=feature_id,
                name=option.name,
                canonical_name=option.name,
                summary=option.description,
                lifecycle_stage=option.lifecycle_stage,
                will_be_enforced=option.will_be_enforced,
                prod_account_state=option.prod_account_state,
                prod_course_state=option.prod_course_state,
                beta_account_state=option.beta_account_state,
                beta_course_state=option.beta_course_state,
                source='canonical_page',
                doc_url=option.doc_url,
                user_group_url=option.user_group_url,
            )
            upserted += 1
        except Exception as e:
            logger.warning(
                "Failed to upsert canonical option '%s': %s",
                option.name, e,
            )

    logger.info(
        "Upserted %d of %d canonical feature options into database",
        upserted, len(options),
    )
    return options
