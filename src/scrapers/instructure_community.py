"""Scraper for Instructure Canvas Community release notes and changelog."""

import logging
import time
import re
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

if TYPE_CHECKING:
    from utils.database import Database

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    PlaywrightTimeout = Exception

logger = logging.getLogger("canvas_rss")


@dataclass
class CommunityPost:
    """A post from the Instructure Canvas Community."""

    title: str
    url: str
    content: str
    published_date: datetime
    likes: int = 0
    comments: int = 0
    post_type: str = "discussion"  # 'release_note', 'changelog', 'question', 'blog'
    is_latest: bool = False  # True if tagged as "Latest Release" or "Latest Deploy"
    # v2.0 source date fields
    first_posted: Optional[datetime] = None
    last_edited: Optional[datetime] = None
    last_comment_at: Optional[datetime] = None
    comment_count: int = 0

    @property
    def source(self) -> str:
        """Return the source type for this post."""
        return "community"

    @property
    def source_id(self) -> str:
        """Generate unique ID from URL and post type."""
        return extract_source_id(self.url, self.post_type)


@dataclass
class DiscussionUpdate:
    """Represents a discussion post that is new or has new comments."""
    post: CommunityPost
    is_new: bool
    previous_comment_count: int
    new_comment_count: int
    latest_comment: Optional[str]


@dataclass
class FeatureTableData:
    """Configuration table data for a release/deploy feature."""
    enable_location: str
    default_status: str
    permissions: str
    affected_areas: List[str]
    affects_roles: List[str]


@dataclass
class Feature:
    """A single feature from a Release/Deploy Notes page."""
    category: str
    name: str
    anchor_id: str
    added_date: Optional[datetime]
    raw_content: str
    table_data: Optional[FeatureTableData]


@dataclass
class UpcomingChange:
    """An upcoming Canvas change/deprecation."""
    date: datetime
    description: str
    days_until: int


@dataclass
class ReleaseNotePage:
    """A parsed Release Notes page with all features."""
    title: str
    url: str
    release_date: datetime
    upcoming_changes: List[UpcomingChange]
    features: List[Feature]
    sections: Dict[str, List[Feature]]
    # v2.0 source date fields
    first_posted: Optional[datetime] = None
    last_edited: Optional[datetime] = None


@dataclass
class DeployChange:
    """A single change from a Deploy Notes page."""
    category: str
    name: str
    anchor_id: str
    section: str
    raw_content: str
    table_data: Optional[FeatureTableData]
    status: Optional[str]  # "delayed", None
    status_date: Optional[datetime]


@dataclass
class DeployNotePage:
    """A parsed Deploy Notes page with all changes."""
    title: str
    url: str
    deploy_date: datetime
    beta_date: Optional[datetime]
    changes: List[DeployChange]
    sections: Dict[str, List[DeployChange]]
    # v2.0 source date fields
    first_posted: Optional[datetime] = None
    last_edited: Optional[datetime] = None


def extract_source_id(url: str, post_type: str) -> str:
    """Extract numeric ID from Instructure Community URL.

    Args:
        url: Full URL to a community post.
        post_type: Type of post ('question', 'blog', etc.).

    Returns:
        Source ID in format '{post_type}_{numeric_id}'.
    """
    match = re.search(r'/(discussion|blog)/(\d+)', url)
    if match:
        return f"{post_type}_{match.group(2)}"
    return f"{post_type}_{abs(hash(url))}"


# Keep legacy classes for backwards compatibility
@dataclass
class ReleaseNote:
    """A release note from the Canvas Community."""

    title: str
    url: str
    content: str
    published_date: datetime
    likes: int = 0
    comments: int = 0
    post_type: str = "release_note"  # 'release_note' or 'deploy_note'
    is_latest: bool = False  # True if tagged as "Latest Release" or "Latest Deploy"
    # v2.0 source date fields
    first_posted: Optional[datetime] = None
    last_edited: Optional[datetime] = None

    @property
    def source(self) -> str:
        """Return the source type for this release note."""
        return "community"

    @property
    def source_id(self) -> str:
        """Generate unique ID from URL and post type."""
        return extract_source_id(self.url, self.post_type)


@dataclass
class ChangeLogEntry:
    """A changelog entry from the Canvas API changelog."""

    title: str
    url: str
    content: str
    published_date: datetime

    @property
    def source(self) -> str:
        """Return the source type for this changelog entry."""
        return "community"

    @property
    def source_id(self) -> str:
        """Generate unique ID from URL."""
        return f"changelog_{hash(self.url)}"


class InstructureScraper:
    """Scrape Canvas Community release notes and change logs.

    Uses Playwright sync API for JavaScript-rendered page scraping.
    """

    RELEASE_NOTES_URL = "https://community.instructure.com/en/categories/canvas-release-notes/"
    CHANGELOG_URL = "https://community.instructure.com/en/categories/canvas-lms-changelog"
    # Sort by most recently commented for discussion-focused content
    QUESTION_FORUM_URL = "https://community.instructure.com/en/categories/canvas-lms-question-forum?sort=-dateLastComment"
    BLOG_URL = "https://community.instructure.com/en/categories/canvas_lms_blog?sort=-dateLastComment"
    USER_AGENT = "Canvas-RSS-Aggregator/1.0 (Educational Use)"

    # Title patterns for Deploy Notes (bug fixes, patches) - check first, more specific
    DEPLOY_NOTE_PATTERNS = [
        r"Canvas Deploy Notes",
        r"Deploy Notes \(\d{4}",
        r"Canvas \(\w+\) Deploy Notes",
    ]

    # Title patterns for Release Notes (new features)
    RELEASE_NOTE_PATTERNS = [
        r"Canvas Release Notes",
        r"Release Notes \(\d{4}",
        r"Canvas \(\w+\) Release Notes",
    ]

    # Blog filtering - only include Product Overview posts
    BLOG_PRODUCT_OVERVIEW_PATTERNS = [
        r"Product Overview",
        r"\| Product Overview",
    ]

    # Q&A engagement threshold (likes + comments)
    MIN_QA_ENGAGEMENT = 5

    def __init__(self, headless: bool = True, rate_limit_seconds: float = 3.0):
        """Initialize the scraper with Playwright browser.

        Args:
            headless: Run browser in headless mode (default: True).
            rate_limit_seconds: Delay between page navigations (default: 3.0).
        """
        self.headless = headless
        self.rate_limit_seconds = rate_limit_seconds
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        if not PLAYWRIGHT_AVAILABLE:
            logger.warning(
                "Playwright is not installed. Instructure Community scraping will be disabled. "
                "Install with: pip install playwright && playwright install chromium"
            )
            return

        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.context = self.browser.new_context(
                user_agent=self.USER_AGENT
            )
            self.page = self.context.new_page()
            logger.info("Playwright browser initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Playwright browser: {e}")
            self._cleanup_partial()

    def _cleanup_partial(self):
        """Clean up partially initialized resources."""
        if self.page:
            try:
                self.page.close()
            except Exception:
                pass
            self.page = None
        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
            self.context = None
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        if self.rate_limit_seconds > 0:
            time.sleep(self.rate_limit_seconds)

    def _classify_release_or_deploy(self, title: str) -> str:
        """Classify a post as release_note or deploy_note based on title.

        Deploy Notes focus on bug fixes, performance improvements, and feature prep.
        Release Notes focus on new features and major changes.

        Args:
            title: Post title to classify.

        Returns:
            'deploy_note' or 'release_note'
        """
        # Check deploy note patterns first (more specific)
        for pattern in self.DEPLOY_NOTE_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return "deploy_note"

        # Check release note patterns
        for pattern in self.RELEASE_NOTE_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return "release_note"

        # Default to release_note for posts from release notes category
        return "release_note"

    def _is_product_overview_blog(self, title: str) -> bool:
        """Check if blog post is a Product Overview post.

        Args:
            title: Post title to check.

        Returns:
            True if this is a Product Overview blog post.
        """
        for pattern in self.BLOG_PRODUCT_OVERVIEW_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        return False

    def _parse_relative_date(self, date_text: str) -> Optional[datetime]:
        """Parse relative date strings like '2 hours ago', 'Yesterday', etc.

        Args:
            date_text: String containing relative or absolute date.

        Returns:
            datetime object or None if parsing fails.
        """
        if not date_text:
            return None

        date_text = date_text.strip().lower()
        now = datetime.now(timezone.utc)

        try:
            # Handle "X minutes/hours/days ago" patterns
            if "ago" in date_text:
                # Extract number and unit
                match = re.search(r'(\d+)\s*(second|minute|hour|day|week|month)s?\s*ago', date_text)
                if match:
                    value = int(match.group(1))
                    unit = match.group(2)

                    if unit == "second":
                        return now - timedelta(seconds=value)
                    elif unit == "minute":
                        return now - timedelta(minutes=value)
                    elif unit == "hour":
                        return now - timedelta(hours=value)
                    elif unit == "day":
                        return now - timedelta(days=value)
                    elif unit == "week":
                        return now - timedelta(weeks=value)
                    elif unit == "month":
                        return now - timedelta(days=value * 30)

            # Handle "yesterday"
            if "yesterday" in date_text:
                return now - timedelta(days=1)

            # Handle "today"
            if "today" in date_text:
                return now

            # Handle "just now" or "moments ago"
            if "just now" in date_text or "moments ago" in date_text:
                return now

            # Try ISO format
            if "t" in date_text or "-" in date_text:
                # Clean up common variations
                clean_date = date_text.replace("z", "+00:00")
                if clean_date.endswith("+00:00+00:00"):
                    clean_date = clean_date[:-6]
                return datetime.fromisoformat(clean_date)

            # Try common date formats
            for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    parsed = datetime.strptime(date_text, fmt)
                    return parsed.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

        except Exception as e:
            logger.debug(f"Could not parse date '{date_text}': {e}")

        return None

    def _is_within_hours(self, dt: Optional[datetime], hours: int = 24) -> bool:
        """Check if datetime is within the last N hours.

        Args:
            dt: datetime to check.
            hours: Number of hours to look back (default: 24).

        Returns:
            True if datetime is within the time window.
        """
        if not dt:
            return False

        now = datetime.now(timezone.utc)

        # Ensure datetime is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        cutoff = now - timedelta(hours=hours)
        return dt >= cutoff

    def _scroll_to_load_posts(self, max_scrolls: int = 5) -> None:
        """Scroll down to trigger infinite scroll and load more posts.

        Args:
            max_scrolls: Maximum number of scroll iterations (default: 5).
        """
        if not self.page:
            return

        previous_height = 0
        for i in range(max_scrolls):
            # Get current scroll height
            current_height = self.page.evaluate("document.body.scrollHeight")

            # If height hasn't changed, we've likely loaded all content
            if current_height == previous_height:
                logger.debug(f"Scroll stopped at iteration {i+1} - no new content loaded")
                break

            previous_height = current_height

            # Scroll to bottom
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(1500)  # Wait for content to load

            # Log progress
            post_count = len(self.page.query_selector_all("h3 a") or [])
            logger.debug(f"Scroll {i+1}/{max_scrolls}: found {post_count} post links")

    def _dismiss_cookie_consent(self) -> None:
        """Dismiss cookie consent banner if present."""
        if not self.page:
            return

        try:
            # Look for common cookie consent buttons
            accept_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("I Accept")',
                '[id*="accept"]',
                '[class*="accept"]',
            ]

            for selector in accept_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        self.page.wait_for_timeout(1000)
                        logger.debug("Dismissed cookie consent banner")
                        return
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"No cookie consent to dismiss: {e}")

    def _extract_post_cards(self) -> List[dict]:
        """Extract post card information from the current page.

        Returns:
            List of dicts with title, url, date_text for each post.
        """
        posts = []

        if not self.page:
            return posts

        try:
            # Wait for content to load
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # Dismiss cookie consent if present
            self._dismiss_cookie_consent()

            # Wait a bit more for content to render after dismissing cookie banner
            self.page.wait_for_timeout(2000)

            # Scroll to load more posts (infinite scroll pages)
            self._scroll_to_load_posts(max_scrolls=5)

            # Try multiple selector strategies for community posts
            # Instructure Community uses various card/list layouts
            selectors = [
                # H3 links (common in Instructure Community)
                "h3 a[href*='/discussion/']",
                "h3 a[href*='/blog/']",
                "h3 a",
                # Card-based layouts
                "article",
                "[class*='topic-list'] [class*='item']",
                "[class*='post-list'] [class*='item']",
                "[class*='topic'] a[href*='/discussion/']",
                "[class*='card'] a[href*='/discussion/']",
                # List-based layouts
                "li[class*='topic']",
                "tr[class*='topic']",
                # Generic content containers
                ".content-list-item",
                "[data-testid*='topic']",
                "[data-testid*='post']",
                # Link-based extraction as fallback
                "a[href*='/discussion/']",
                "a[href*='/t/']",
            ]

            for selector in selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    if elements:
                        logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                        break
                except Exception:
                    continue
            else:
                # No elements found with any selector
                logger.warning("Could not find post elements on page")
                return posts

            # Extract data from found elements
            for element in elements[:50]:  # Limit to 50 posts
                try:
                    # Try to find title and URL
                    title = ""
                    url = ""
                    date_text = ""

                    # Check if element is a link
                    tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                    if tag_name == "a":
                        title = element.inner_text().strip()
                        url = element.get_attribute("href") or ""
                    else:
                        # Find link within element - check for /discussion/ first, then /t/
                        link = (
                            element.query_selector("a[href*='/discussion/']") or
                            element.query_selector("a[href*='/t/']") or
                            element.query_selector("a")
                        )
                        if link:
                            title = link.inner_text().strip()
                            url = link.get_attribute("href") or ""

                    # Look for date information
                    date_element = (
                        element.query_selector("time") or
                        element.query_selector("[class*='date']") or
                        element.query_selector("[class*='time']") or
                        element.query_selector("[datetime]")
                    )
                    if date_element:
                        date_text = (
                            date_element.get_attribute("datetime") or
                            date_element.get_attribute("title") or
                            date_element.inner_text()
                        )

                    # Skip if we don't have minimum required data
                    if not title or not url:
                        continue

                    # Make URL absolute
                    if url.startswith("/"):
                        url = f"https://community.instructure.com{url}"

                    # Skip if URL doesn't look like a post
                    if "/t/" not in url and "/topic" not in url.lower() and "/discussion/" not in url and "/blog/" not in url:
                        continue

                    # Skip comment URLs (these are replies, not main posts)
                    if "/comment/" in url or "#Comment_" in url:
                        continue

                    posts.append({
                        "title": title[:500],  # Limit title length
                        "url": url,
                        "date_text": date_text
                    })

                except Exception as e:
                    logger.debug(f"Error extracting post card: {e}")
                    continue

            # Deduplicate by URL
            seen_urls = set()
            unique_posts = []
            for post in posts:
                if post["url"] not in seen_urls:
                    seen_urls.add(post["url"])
                    unique_posts.append(post)

            return unique_posts

        except PlaywrightTimeout:
            logger.warning("Timeout waiting for post cards to load")
            return []
        except Exception as e:
            logger.error(f"Error extracting post cards: {e}")
            return []

    def _get_post_content(self, url: str) -> dict:
        """Navigate to a post and extract its content and metadata.

        Args:
            url: URL of the post to scrape.

        Returns:
            Dictionary with keys: content, likes, comments, first_posted,
            last_edited, last_comment_at, comment_count.
        """
        result = {
            "content": "",
            "likes": 0,
            "comments": 0,
            "first_posted": None,
            "last_edited": None,
            "last_comment_at": None,
            "comment_count": 0,
        }

        if not self.page:
            return result

        try:
            self._rate_limit()
            self.page.goto(url, timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # Extract main content
            content_selectors = [
                "[class*='post-content']",
                "[class*='topic-content']",
                "[class*='message-body']",
                "article [class*='content']",
                ".post-body",
                ".topic-body",
                "article",
                "main [class*='content']",
            ]

            for selector in content_selectors:
                try:
                    content_el = self.page.query_selector(selector)
                    if content_el:
                        result["content"] = content_el.inner_text().strip()
                        if len(result["content"]) > 50:  # Found substantial content
                            break
                except Exception:
                    continue

            # Limit content length
            result["content"] = result["content"][:5000] if result["content"] else ""

            # Extract likes/reactions
            likes_selectors = [
                "[class*='like-count']",
                "[class*='kudos']",
                "[class*='reaction-count']",
                "[aria-label*='like']",
                "[title*='like']",
            ]

            for selector in likes_selectors:
                try:
                    likes_el = self.page.query_selector(selector)
                    if likes_el:
                        likes_text = likes_el.inner_text().strip()
                        likes_match = re.search(r'(\d+)', likes_text)
                        if likes_match:
                            result["likes"] = int(likes_match.group(1))
                            break
                except Exception:
                    continue

            # Extract comment count from reply count or pagination
            comments_selectors = [
                "[class*='comment-count']",
                "[class*='reply-count']",
                "[class*='replies']",
                "[aria-label*='comment']",
                "[aria-label*='repl']",
            ]

            for selector in comments_selectors:
                try:
                    comments_el = self.page.query_selector(selector)
                    if comments_el:
                        comments_text = comments_el.inner_text().strip()
                        comments_match = re.search(r'(\d+)', comments_text)
                        if comments_match:
                            result["comments"] = int(comments_match.group(1))
                            result["comment_count"] = result["comments"]
                            break
                except Exception:
                    continue

            # Extract first_posted from first <time datetime> element
            try:
                time_elements = self.page.query_selector_all("time[datetime]")
                if time_elements:
                    first_time = time_elements[0]
                    dt_str = first_time.get_attribute("datetime")
                    if dt_str:
                        result["first_posted"] = self._parse_relative_date(dt_str)
            except Exception as e:
                logger.debug(f"Error extracting first_posted: {e}")

            # Extract last_edited - look for "Edited" or "Updated" time elements
            try:
                edit_selectors = [
                    "[class*='edited'] time[datetime]",
                    "[class*='updated'] time[datetime]",
                ]
                for selector in edit_selectors:
                    try:
                        edited_el = self.page.query_selector(selector)
                        if edited_el:
                            dt_str = edited_el.get_attribute("datetime")
                            if dt_str:
                                result["last_edited"] = self._parse_relative_date(dt_str)
                                break
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Error extracting last_edited: {e}")

            # Extract last_comment_at from the last comment's time element
            try:
                comment_section_selectors = [
                    "[class*='comment']",
                    "[class*='reply']",
                    "[class*='response']",
                ]
                for section_selector in comment_section_selectors:
                    try:
                        comments = self.page.query_selector_all(section_selector)
                        if comments and len(comments) > 1:
                            last_comment = comments[-1]
                            time_el = last_comment.query_selector("time[datetime]")
                            if time_el:
                                dt_str = time_el.get_attribute("datetime")
                                if dt_str:
                                    result["last_comment_at"] = self._parse_relative_date(dt_str)
                                    break
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Error extracting last_comment_at: {e}")

            return result

        except PlaywrightTimeout:
            logger.warning(f"Timeout loading post: {url}")
            return result
        except Exception as e:
            logger.error(f"Error getting post content from {url}: {e}")
            return result

    def _click_deploys_tab(self) -> bool:
        """Click the Deploys tab to switch to deploy notes view.

        Returns:
            True if successfully clicked, False otherwise.
        """
        if not self.page:
            return False

        try:
            # Playwright text selectors - try exact text match first
            deploy_selectors = [
                'text="Deploys"',
                'text=Deploys',
                ':text("Deploys")',
                'a:has-text("Deploys")',
                'button:has-text("Deploys")',
                '[role="tab"]:has-text("Deploys")',
                '[class*="tab"]:has-text("Deploys")',
            ]

            for selector in deploy_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible(timeout=2000):
                        element.click()
                        self.page.wait_for_timeout(2000)
                        logger.info("Clicked Deploys tab successfully")
                        return True
                except Exception:
                    continue

            logger.warning("Could not find Deploys tab to click")
            return False

        except Exception as e:
            logger.error(f"Error clicking Deploys tab: {e}")
            return False

    def _detect_latest_badge(self, post_element) -> bool:
        """Detect if a post has a 'Latest Release' or 'Latest Deploy' badge.

        Args:
            post_element: Playwright element handle for the post.

        Returns:
            True if the post has a "Latest" badge.
        """
        try:
            # Look for common badge/label patterns
            badge_selectors = [
                '[class*="latest"]',
                '[class*="badge"]',
                'span:has-text("Latest")',
                '[data-testid*="latest"]',
            ]

            for selector in badge_selectors:
                try:
                    badge = post_element.query_selector(selector)
                    if badge:
                        badge_text = badge.inner_text().lower()
                        if "latest" in badge_text:
                            return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.debug(f"Error detecting latest badge: {e}")
            return False

    def _get_next_sibling_content(self, heading) -> str:
        """Extract content between this heading and the next heading.

        Args:
            heading: Playwright element handle for an h2/h3/h4 heading.

        Returns:
            HTML content string of all siblings until next heading.
        """
        try:
            # Get all siblings until next heading
            content = heading.evaluate("""
                el => {
                    let content = [];
                    let sibling = el.nextElementSibling;
                    while (sibling && !sibling.matches('h1, h2, h3, h4, h5, h6')) {
                        content.push(sibling.outerHTML);
                        sibling = sibling.nextElementSibling;
                    }
                    return content.join('');
                }
            """)
            return content or ""
        except Exception as e:
            logger.debug(f"Error extracting sibling content: {e}")
            return ""

    def _parse_feature_table(self, raw_content: str) -> Optional[FeatureTableData]:
        """Parse configuration table from feature content.

        Args:
            raw_content: HTML string that may contain a feature configuration table.

        Returns:
            FeatureTableData if a table is found and parsed, None otherwise.
        """
        if not raw_content or '<table' not in raw_content.lower():
            return None

        try:
            # Use BeautifulSoup for table parsing
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw_content, 'html.parser')
            table = soup.find('table')
            if not table:
                return None

            data = {}
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text().strip().lower()
                    value = cells[1].get_text().strip()
                    data[key] = value

            return FeatureTableData(
                enable_location=data.get('enabled', data.get('enable', data.get('enabled at', ''))),
                default_status=data.get('default', data.get('default status', '')),
                permissions=data.get('permissions', data.get('permission', '')),
                affected_areas=self._extract_areas(data.get('affects', data.get('affected areas', ''))),
                affects_roles=self._extract_roles(data.get('affects', data.get('roles', '')))
            )
        except Exception as e:
            logger.debug(f"Error parsing feature table: {e}")
            return None

    def _extract_areas(self, text: str) -> List[str]:
        """Extract affected areas from text.

        Args:
            text: String like "Gradebook, Assignments, Quizzes".

        Returns:
            List of area names.
        """
        if not text:
            return []
        # Split by comma and clean up
        return [area.strip() for area in text.split(',') if area.strip()]

    def _extract_roles(self, text: str) -> List[str]:
        """Extract affected roles from text.

        Args:
            text: String like "Instructors, Admins".

        Returns:
            List of role names.
        """
        if not text:
            return []
        # Common role keywords to look for
        role_keywords = ['instructor', 'student', 'admin', 'teacher', 'ta', 'observer', 'designer']
        text_lower = text.lower()
        found_roles = []
        for role in role_keywords:
            if role in text_lower:
                found_roles.append(role.capitalize())
        return found_roles if found_roles else [r.strip() for r in text.split(',') if r.strip()]

    def _scrape_notes_from_current_view(
        self, hours: int, post_type: str, skip_date_filter: bool = False
    ) -> List[ReleaseNote]:
        """Scrape notes from the currently displayed view.

        Args:
            hours: Number of hours to look back.
            post_type: Type of post ('release_note' or 'deploy_note').
            skip_date_filter: If True, skip date filtering (e.g., for first run).

        Returns:
            List of ReleaseNote objects.
        """
        notes = []
        filtered_count = 0

        try:
            # Extract post cards from current view
            posts = self._extract_post_cards()
            logger.info(f"Found {len(posts)} posts in {post_type} view")

            for post in posts:
                published_date = self._parse_relative_date(post.get("date_text", ""))

                if not skip_date_filter and published_date and not self._is_within_hours(published_date, hours):
                    filtered_count += 1
                    logger.debug(f"Skipping old post (>{hours}h): {post['title']}")
                    continue

                # Get full content and metadata
                post_data = self._get_post_content(post["url"])

                if not published_date:
                    published_date = datetime.now(timezone.utc)

                # Detect if this is marked as "Latest"
                is_latest = "latest" in post.get("title", "").lower() or \
                           "latest" in post.get("badge", "").lower() if post.get("badge") else False

                note = ReleaseNote(
                    title=post["title"],
                    url=post["url"],
                    content=post_data["content"],
                    published_date=published_date,
                    likes=post_data["likes"],
                    comments=post_data["comments"],
                    post_type=post_type,
                    is_latest=is_latest
                )
                notes.append(note)
                logger.debug(f"Scraped {post_type}: {post['title'][:50]}...")

            if filtered_count > 0:
                logger.info(f"Filtered {filtered_count} {post_type}s older than {hours}h")

            return notes

        except Exception as e:
            logger.error(f"Error scraping {post_type} view: {e}")
            return notes

    def scrape_release_notes(self, hours: int = 24, skip_date_filter: bool = False) -> List[ReleaseNote]:
        """Get posts from last N hours from release notes category.

        Scrapes both Release Notes (Releases tab) and Deploy Notes (Deploys tab).

        Args:
            hours: Number of hours to look back (default: 24).
            skip_date_filter: If True, skip date filtering (e.g., for first run).

        Returns:
            List of ReleaseNote objects for recent posts (both release and deploy notes).
        """
        if not self.page:
            logger.warning("Browser not available, returning empty release notes list")
            return []

        all_notes = []

        try:
            # 1. Navigate to release notes page and scrape release notes (default view)
            logger.info(f"Scraping release notes from {self.RELEASE_NOTES_URL}")
            self.page.goto(self.RELEASE_NOTES_URL, timeout=60000)

            # Wait for page to load (increased timeout for slow networks)
            self.page.wait_for_load_state("networkidle", timeout=45000)
            self._dismiss_cookie_consent()
            self.page.wait_for_timeout(2000)

            # Scrape release notes from default Releases view
            release_notes = self._scrape_notes_from_current_view(hours, "release_note", skip_date_filter)
            all_notes.extend(release_notes)
            logger.info(f"Scraped {len(release_notes)} release notes")

            # 2. Navigate back to category page (scraping navigates to each post for content)
            logger.info("Switching to Deploy Notes view...")
            self.page.goto(self.RELEASE_NOTES_URL, timeout=60000)
            self.page.wait_for_load_state("networkidle", timeout=45000)
            self._dismiss_cookie_consent()
            self.page.wait_for_timeout(2000)
            if self._click_deploys_tab():
                # Wait for the deploy notes to load
                self.page.wait_for_load_state("networkidle", timeout=45000)
                self.page.wait_for_timeout(2000)

                deploy_notes = self._scrape_notes_from_current_view(hours, "deploy_note", skip_date_filter)
                all_notes.extend(deploy_notes)
                logger.info(f"Scraped {len(deploy_notes)} deploy notes")
            else:
                # Fallback: log warning but continue with what we have
                logger.warning(
                    "Could not click Deploys tab. "
                    "Deploy notes may be missed."
                )

            logger.info(
                f"Total: {len(all_notes)} notes "
                f"({len(release_notes)} release, {len(all_notes) - len(release_notes)} deploy)"
            )
            return all_notes

        except PlaywrightTimeout:
            logger.error(f"Timeout loading release notes page: {self.RELEASE_NOTES_URL}")
            return all_notes  # Return any notes we managed to scrape
        except Exception as e:
            logger.error(f"Error scraping release notes: {e}")
            return all_notes  # Return any notes we managed to scrape

    def scrape_changelog(self, hours: int = 24) -> List[ChangeLogEntry]:
        """Get API change log entries from last N hours.

        Args:
            hours: Number of hours to look back (default: 24).

        Returns:
            List of ChangeLogEntry objects for recent entries.
        """
        if not self.page:
            logger.warning("Browser not available, returning empty changelog list")
            return []

        changelog_entries = []

        try:
            logger.info(f"Scraping changelog from {self.CHANGELOG_URL}")
            self.page.goto(self.CHANGELOG_URL, timeout=30000)

            # Extract post cards
            posts = self._extract_post_cards()
            logger.info(f"Found {len(posts)} total posts on changelog page")

            # Filter to recent posts and get full content
            for post in posts:
                published_date = self._parse_relative_date(post.get("date_text", ""))

                # Filter by date if we have one
                if published_date and not self._is_within_hours(published_date, hours):
                    logger.debug(f"Skipping old changelog entry: {post['title']}")
                    continue

                # Get full content
                post_data = self._get_post_content(post["url"])

                # Use current time if we couldn't parse the date
                if not published_date:
                    published_date = datetime.now(timezone.utc)

                entry = ChangeLogEntry(
                    title=post["title"],
                    url=post["url"],
                    content=post_data["content"],
                    published_date=published_date
                )
                changelog_entries.append(entry)

            logger.info(f"Scraped {len(changelog_entries)} changelog entries from last {hours} hours")
            return changelog_entries

        except PlaywrightTimeout:
            logger.error(f"Timeout loading changelog page: {self.CHANGELOG_URL}")
            return []
        except Exception as e:
            logger.error(f"Error scraping changelog: {e}")
            return []

    def scrape_question_forum(self, hours: int = 24) -> List[CommunityPost]:
        """Get Q&A posts from the Canvas LMS question forum.

        Args:
            hours: Number of hours to look back (default: 24).

        Returns:
            List of CommunityPost objects for recent questions.
        """
        if not self.page:
            logger.warning("Browser not available, returning empty question forum list")
            return []

        posts = []

        try:
            logger.info(f"Scraping question forum from {self.QUESTION_FORUM_URL}")
            self.page.goto(self.QUESTION_FORUM_URL, timeout=30000)

            # Extract post cards
            post_cards = self._extract_post_cards()
            logger.info(f"Found {len(post_cards)} total posts on question forum page")

            # Get recent posts with full content
            for post in post_cards:
                published_date = self._parse_relative_date(post.get("date_text", ""))

                if published_date and not self._is_within_hours(published_date, hours):
                    logger.debug(f"Skipping old question: {post['title']}")
                    continue

                # Get full content (includes engagement metrics and source dates)
                post_data = self._get_post_content(post["url"])

                if not published_date:
                    published_date = datetime.now(timezone.utc)

                community_post = CommunityPost(
                    title=post["title"],
                    url=post["url"],
                    content=post_data["content"],
                    published_date=published_date,
                    likes=post_data["likes"],
                    comments=post_data["comments"],
                    post_type="question",
                    first_posted=post_data["first_posted"],
                    last_edited=post_data["last_edited"],
                    last_comment_at=post_data["last_comment_at"],
                    comment_count=post_data["comment_count"],
                )
                posts.append(community_post)

            logger.info(f"Scraped {len(posts)} questions from last {hours} hours")
            return posts

        except PlaywrightTimeout:
            logger.error(f"Timeout loading question forum: {self.QUESTION_FORUM_URL}")
            return []
        except Exception as e:
            logger.error(f"Error scraping question forum: {e}")
            return []

    def scrape_blog(self, hours: int = 24) -> List[CommunityPost]:
        """Get blog posts from the Canvas LMS blog.

        Args:
            hours: Number of hours to look back (default: 24).

        Returns:
            List of CommunityPost objects for recent blog posts.
        """
        if not self.page:
            logger.warning("Browser not available, returning empty blog list")
            return []

        posts = []

        try:
            logger.info(f"Scraping blog from {self.BLOG_URL}")
            self.page.goto(self.BLOG_URL, timeout=30000)

            # Extract post cards
            post_cards = self._extract_post_cards()
            logger.info(f"Found {len(post_cards)} total posts on blog page")

            # Get recent posts with full content
            for post in post_cards:
                published_date = self._parse_relative_date(post.get("date_text", ""))

                if published_date and not self._is_within_hours(published_date, hours):
                    logger.debug(f"Skipping old blog post: {post['title']}")
                    continue

                # Get full content and source dates
                post_data = self._get_post_content(post["url"])

                if not published_date:
                    published_date = datetime.now(timezone.utc)

                community_post = CommunityPost(
                    title=post["title"],
                    url=post["url"],
                    content=post_data["content"],
                    published_date=published_date,
                    likes=post_data["likes"],
                    comments=post_data["comments"],
                    post_type="blog",
                    first_posted=post_data["first_posted"],
                    last_edited=post_data["last_edited"],
                    last_comment_at=post_data["last_comment_at"],
                    comment_count=post_data["comment_count"],
                )
                posts.append(community_post)

            logger.info(f"Scraped {len(posts)} blog posts from last {hours} hours")
            return posts

        except PlaywrightTimeout:
            logger.error(f"Timeout loading blog: {self.BLOG_URL}")
            return []
        except Exception as e:
            logger.error(f"Error scraping blog: {e}")
            return []

    def scrape_all(self, hours: int = 24, skip_date_filter: bool = False) -> List[CommunityPost]:
        """Scrape all community sources and return unified list.

        Scrapes release notes, changelog, Q&A forum, and blog posts.

        Args:
            hours: Number of hours to look back (default: 24).
            skip_date_filter: If True, skip date filtering (e.g., for first run).

        Returns:
            List of CommunityPost objects from all sources.
        """
        all_posts = []

        # Scrape release notes (includes both release and deploy notes) and convert to CommunityPost
        release_notes = self.scrape_release_notes(hours, skip_date_filter)
        for note in release_notes:
            post = CommunityPost(
                title=note.title,
                url=note.url,
                content=note.content,
                published_date=note.published_date,
                likes=note.likes,
                comments=note.comments,
                post_type=note.post_type,  # Preserve the actual type (release_note or deploy_note)
                is_latest=note.is_latest,  # Preserve the Latest badge status
            )
            all_posts.append(post)

        # Scrape Q&A forum
        questions = self.scrape_question_forum(hours)
        all_posts.extend(questions)

        # Scrape blog
        blog_posts = self.scrape_blog(hours)
        all_posts.extend(blog_posts)

        logger.info(
            f"Scraped {len(all_posts)} total community posts: "
            f"{len(release_notes)} release notes, "
            f"{len(questions)} questions, {len(blog_posts)} blog posts"
        )
        return all_posts

    def scrape_latest_comment(self, url: str) -> Optional[str]:
        """Navigate to a post and extract the most recent comment.

        Args:
            url: URL of the community post.

        Returns:
            Text of the latest comment (max 500 chars), or None.
        """
        if not self.page:
            return None

        try:
            self._rate_limit()
            self.page.goto(url, timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            comment_selectors = [
                "[class*='comment']:last-child",
                "[class*='reply']:last-of-type",
                "[class*='message']:last-child",
                "[class*='Comment']:last-child",
            ]

            for selector in comment_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        text = element.inner_text().strip()
                        if text and len(text) > 10:
                            return text[:500] if len(text) > 500 else text
                except Exception:
                    continue

            return None

        except PlaywrightTimeout:
            logger.warning(f"Timeout scraping comment from: {url}")
            return None
        except Exception as e:
            logger.error(f"Error scraping comment from {url}: {e}")
            return None

    def parse_release_note_page(self, url: str) -> Optional[ReleaseNotePage]:
        """Parse a Release Notes page into structured data.

        Args:
            url: URL of the release notes page.

        Returns:
            ReleaseNotePage with features, or None on error.
        """
        if not self.page:
            return None

        try:
            self._rate_limit()
            self.page.goto(url, timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            title = self.page.title() or "Canvas Release Notes"

            # Extract date from title
            date_match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', title)
            if date_match:
                release_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
            else:
                release_date = datetime.now(timezone.utc)

            features = []
            sections: Dict[str, List[Feature]] = {}
            upcoming_changes: List[UpcomingChange] = []
            current_section = "New Features"
            current_category = "General"

            # Task 11: Parse Upcoming Canvas Changes section
            upcoming_section = self.page.query_selector("[data-id='upcoming-canvas-changes'], h2[data-id*='upcoming']")
            if upcoming_section:
                try:
                    # Get list items within or after the upcoming changes section
                    list_items = upcoming_section.evaluate("""
                        el => {
                            // Try to find list items after this heading
                            let items = [];
                            let sibling = el.nextElementSibling;
                            while (sibling && !sibling.matches('h1, h2')) {
                                if (sibling.tagName === 'UL' || sibling.tagName === 'OL') {
                                    const lis = sibling.querySelectorAll('li');
                                    lis.forEach(li => items.push(li.innerText));
                                }
                                sibling = sibling.nextElementSibling;
                            }
                            return items;
                        }
                    """)
                    for item_text in list_items:
                        if item_text:
                            # Parse date from text (e.g., "2026-02-15: Feature deprecation")
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', item_text)
                            if date_match:
                                change_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                                days_until = (change_date - datetime.now()).days
                                # Remove date prefix from description
                                description = re.sub(r'\d{4}-\d{2}-\d{2}[:\s]*', '', item_text).strip()
                                upcoming_changes.append(UpcomingChange(
                                    date=change_date,
                                    description=description,
                                    days_until=max(0, days_until)
                                ))
                except Exception as e:
                    logger.debug(f"Error parsing upcoming changes: {e}")

            # Parse H2 (sections), H3 (categories), H4 (features)
            headings = self.page.query_selector_all("h2[data-id], h3[data-id], h4[data-id]")

            for heading in headings:
                try:
                    tag = heading.evaluate("el => el.tagName.toLowerCase()")
                    data_id = heading.get_attribute("data-id") or ""
                    text = heading.inner_text().strip()

                    if tag == "h2":
                        current_section = text
                        if current_section not in sections:
                            sections[current_section] = []
                    elif tag == "h3":
                        current_category = text
                    elif tag == "h4":
                        # Extract [Added DATE] annotation
                        added_date = None
                        added_match = re.search(r'\[Added (\d{4}-\d{2}-\d{2})\]', text)
                        if added_match:
                            added_date = datetime.strptime(added_match.group(1), "%Y-%m-%d")
                            text = re.sub(r'\s*\[Added \d{4}-\d{2}-\d{2}\]', '', text)

                        # Task 12: Use _get_next_sibling_content for full content extraction
                        raw_content = self._get_next_sibling_content(heading)

                        # Task 12: Parse table data from raw content
                        table_data = self._parse_feature_table(raw_content)

                        feature = Feature(
                            category=current_category,
                            name=text,
                            anchor_id=data_id,
                            added_date=added_date,
                            raw_content=raw_content,
                            table_data=table_data
                        )
                        features.append(feature)

                        if current_section not in sections:
                            sections[current_section] = []
                        sections[current_section].append(feature)
                except Exception as e:
                    logger.debug(f"Error parsing heading: {e}")
                    continue

            # Extract source dates from page
            first_posted = None
            last_edited = None
            try:
                time_elements = self.page.query_selector_all("time[datetime]")
                if time_elements:
                    dt_str = time_elements[0].get_attribute("datetime")
                    if dt_str:
                        first_posted = self._parse_relative_date(dt_str)
                # Look for edited/updated time
                edit_selectors = [
                    "[class*='edited'] time[datetime]",
                    "[class*='updated'] time[datetime]",
                ]
                for selector in edit_selectors:
                    try:
                        edited_el = self.page.query_selector(selector)
                        if edited_el:
                            dt_str = edited_el.get_attribute("datetime")
                            if dt_str:
                                last_edited = self._parse_relative_date(dt_str)
                                break
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Error extracting page dates: {e}")

            return ReleaseNotePage(
                title=title,
                url=url,
                release_date=release_date,
                upcoming_changes=upcoming_changes,
                features=features,
                sections=sections,
                first_posted=first_posted,
                last_edited=last_edited,
            )

        except Exception as e:
            logger.error(f"Error parsing release notes from {url}: {e}")
            return None

    def parse_deploy_note_page(self, url: str) -> Optional[DeployNotePage]:
        """Parse a Deploy Notes page into structured data.

        Args:
            url: URL of the deploy notes page.

        Returns:
            DeployNotePage with changes, or None on error.
        """
        if not self.page:
            return None

        try:
            self._rate_limit()
            self.page.goto(url, timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            title = self.page.title() or "Canvas Deploy Notes"

            # Extract production date from title
            date_match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', title)
            if date_match:
                deploy_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
            else:
                deploy_date = datetime.now(timezone.utc)

            # Try to find beta/production dates in page content
            beta_date = None
            date_info = self.page.query_selector("[class*='date-info'], [class*='deploy-dates'], [class*='schedule']")
            if date_info:
                try:
                    date_text = date_info.inner_text()
                    beta_match = re.search(r'Beta:\s*(\d{4}-\d{2}-\d{2})', date_text)
                    prod_match = re.search(r'Production:\s*(\d{4}-\d{2}-\d{2})', date_text)
                    if beta_match:
                        beta_date = datetime.strptime(beta_match.group(1), "%Y-%m-%d")
                    if prod_match:
                        deploy_date = datetime.strptime(prod_match.group(1), "%Y-%m-%d")
                except Exception as e:
                    logger.debug(f"Error parsing date info: {e}")

            # Parse changes from headings
            changes = []
            sections: Dict[str, List[DeployChange]] = {}
            current_section = "Updated Features"
            current_category = "General"

            headings = self.page.query_selector_all("h2[data-id], h3[data-id], h4[data-id]")

            for heading in headings:
                try:
                    tag = heading.evaluate("el => el.tagName.toLowerCase()")
                    data_id = heading.get_attribute("data-id") or ""
                    text = heading.inner_text().strip()

                    if tag == "h2":
                        current_section = text
                        if current_section not in sections:
                            sections[current_section] = []
                    elif tag == "h3":
                        current_category = text
                    elif tag == "h4":
                        # Parse [Delayed as of DATE] annotation
                        status = None
                        status_date = None
                        delayed_match = re.search(r'\[Delayed as of (\d{4}-\d{2}-\d{2})\]', text)
                        if delayed_match:
                            status = "delayed"
                            status_date = datetime.strptime(delayed_match.group(1), "%Y-%m-%d")
                            text = re.sub(r'\s*\[Delayed as of \d{4}-\d{2}-\d{2}\]', '', text)

                        # Get content after heading
                        raw_content = self._get_next_sibling_content(heading)

                        # Parse table data if present
                        table_data = self._parse_feature_table(raw_content)

                        change = DeployChange(
                            category=current_category,
                            name=text,
                            anchor_id=data_id,
                            section=current_section,
                            raw_content=raw_content,
                            table_data=table_data,
                            status=status,
                            status_date=status_date
                        )
                        changes.append(change)

                        if current_section not in sections:
                            sections[current_section] = []
                        sections[current_section].append(change)
                except Exception as e:
                    logger.debug(f"Error parsing deploy heading: {e}")
                    continue

            # Extract source dates from page
            first_posted = None
            last_edited = None
            try:
                time_elements = self.page.query_selector_all("time[datetime]")
                if time_elements:
                    dt_str = time_elements[0].get_attribute("datetime")
                    if dt_str:
                        first_posted = self._parse_relative_date(dt_str)
                # Look for edited/updated time
                edit_selectors = [
                    "[class*='edited'] time[datetime]",
                    "[class*='updated'] time[datetime]",
                ]
                for selector in edit_selectors:
                    try:
                        edited_el = self.page.query_selector(selector)
                        if edited_el:
                            dt_str = edited_el.get_attribute("datetime")
                            if dt_str:
                                last_edited = self._parse_relative_date(dt_str)
                                break
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Error extracting page dates: {e}")

            return DeployNotePage(
                title=title,
                url=url,
                deploy_date=deploy_date,
                beta_date=beta_date,
                changes=changes,
                sections=sections,
                first_posted=first_posted,
                last_edited=last_edited,
            )

        except Exception as e:
            logger.error(f"Error parsing deploy notes from {url}: {e}")
            return None

    def get_community_reactions(self, post_url: str) -> dict:
        """Extract likes, comments, views from a specific post.

        Args:
            post_url: URL of the community post.

        Returns:
            Dictionary with 'likes', 'comments', 'views' counts.
        """
        result = {"likes": 0, "comments": 0, "views": 0}

        if not self.page:
            logger.warning("Browser not available, returning zero reactions")
            return result

        try:
            self._rate_limit()
            self.page.goto(post_url, timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # Extract likes
            likes_selectors = [
                "[class*='like-count']",
                "[class*='kudos']",
                "[class*='reaction-count']",
                "[aria-label*='like']",
            ]
            for selector in likes_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        text = el.inner_text().strip()
                        match = re.search(r'(\d+)', text)
                        if match:
                            result["likes"] = int(match.group(1))
                            break
                except Exception:
                    continue

            # Extract comments
            comments_selectors = [
                "[class*='comment-count']",
                "[class*='reply-count']",
                "[class*='replies']",
            ]
            for selector in comments_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        text = el.inner_text().strip()
                        match = re.search(r'(\d+)', text)
                        if match:
                            result["comments"] = int(match.group(1))
                            break
                except Exception:
                    continue

            # Extract views
            views_selectors = [
                "[class*='view-count']",
                "[class*='views']",
                "[aria-label*='view']",
            ]
            for selector in views_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        text = el.inner_text().strip()
                        match = re.search(r'(\d+)', text)
                        if match:
                            result["views"] = int(match.group(1))
                            break
                except Exception:
                    continue

            logger.debug(f"Reactions for {post_url}: {result}")
            return result

        except PlaywrightTimeout:
            logger.warning(f"Timeout getting reactions for: {post_url}")
            return result
        except Exception as e:
            logger.error(f"Error getting community reactions from {post_url}: {e}")
            return result

    def close(self):
        """Clean up browser and Playwright resources.

        Safe to call multiple times.
        """
        if self.page:
            try:
                self.page.close()
                logger.debug("Page closed")
            except Exception as e:
                logger.debug(f"Error closing page: {e}")
            self.page = None

        if self.context:
            try:
                self.context.close()
                logger.debug("Context closed")
            except Exception as e:
                logger.debug(f"Error closing context: {e}")
            self.context = None

        if self.browser:
            try:
                self.browser.close()
                logger.debug("Browser closed")
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")
            self.browser = None

        if self.playwright:
            try:
                self.playwright.stop()
                logger.debug("Playwright stopped")
            except Exception as e:
                logger.debug(f"Error stopping Playwright: {e}")
            self.playwright = None

        logger.info("Instructure scraper resources cleaned up")

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context manager exit."""
        self.close()
        return False


def classify_discussion_posts(
    posts: List[CommunityPost],
    db: "Database",
    first_run_limit: int = 5,
    scraper: Optional["InstructureScraper"] = None
) -> List[DiscussionUpdate]:
    """Classify posts as new or updated based on comment tracking.

    Uses the content_items table to track which posts are new vs updated.
    A post is considered:
    - New: if it doesn't exist in the database
    - Updated: if it exists but comment_count has increased

    Args:
        posts: List of CommunityPost objects to classify.
        db: Database instance for checking existing posts.
        first_run_limit: Max posts to include on first run (when db is empty).
        scraper: Optional scraper to fetch latest comment text.

    Returns:
        List of DiscussionUpdate objects for new/updated posts.
    """
    if not posts:
        return []

    updates: List[DiscussionUpdate] = []
    new_posts_count = 0

    # Check if this is a first run (no discussion posts exist in db)
    is_first_run = True
    for post in posts:
        if db.item_exists(post.source_id):
            is_first_run = False
            break

    for post in posts:
        source_id = post.source_id
        current_comment_count = post.comment_count or post.comments or 0

        if not db.item_exists(source_id):
            # New post - check first_run_limit
            if is_first_run and new_posts_count >= first_run_limit:
                continue

            # Get latest comment if scraper available
            latest_comment = None
            if scraper and current_comment_count > 0:
                latest_comment = scraper.scrape_latest_comment(post.url)

            updates.append(DiscussionUpdate(
                post=post,
                is_new=True,
                previous_comment_count=0,
                new_comment_count=current_comment_count,
                latest_comment=latest_comment,
            ))
            new_posts_count += 1
        else:
            # Existing post - check for new comments
            stored_count = db.get_comment_count(source_id) or 0

            if current_comment_count > stored_count:
                # Post has new comments
                latest_comment = None
                if scraper:
                    latest_comment = scraper.scrape_latest_comment(post.url)

                updates.append(DiscussionUpdate(
                    post=post,
                    is_new=False,
                    previous_comment_count=stored_count,
                    new_comment_count=current_comment_count,
                    latest_comment=latest_comment,
                ))

                # Update stored comment count
                db.update_comment_count(source_id, current_comment_count)

    return updates


def classify_release_features(
    page: ReleaseNotePage,
    db: "Database",
    first_run_limit: int = 3
) -> Tuple[bool, List[str]]:
    """Classify release note features as new or existing.

    Creates feature_options records for announced features and links
    the content to features via content_feature_refs.

    Args:
        page: Parsed ReleaseNotePage with features to classify.
        db: Database instance for tracking.
        first_run_limit: Max features to include on first run.

    Returns:
        Tuple of (is_new_page, new_feature_names):
        - is_new_page: True if this release note page is new
        - new_feature_names: List of newly announced feature names
    """
    from src.constants import CANVAS_FEATURES

    if not page or not page.features:
        return (False, [])

    # Generate content_id from the page URL
    content_id = extract_source_id(page.url, "release_note")

    # Check if this page is already tracked
    is_new_page = not db.item_exists(content_id)

    new_feature_names: List[str] = []
    processed_count = 0

    for feature in page.features:
        # Apply first_run_limit for new pages
        if is_new_page and processed_count >= first_run_limit:
            break

        # Generate option_id from anchor_id or name
        option_id = feature.anchor_id if feature.anchor_id else \
            feature.name.lower().replace(' ', '_').replace('-', '_')[:50]

        # Try to match to canonical feature based on category/name
        feature_id = _match_feature_id(feature.category, feature.name, CANVAS_FEATURES)

        # Create/update feature option record
        db.upsert_feature_option(
            option_id=option_id,
            feature_id=feature_id,
            name=feature.name,
            status='pending',  # Release notes announce pending features
            summary=feature.raw_content[:500] if feature.raw_content else None,
            config_level=feature.table_data.enable_location if feature.table_data else None,
            default_state=feature.table_data.default_status if feature.table_data else None,
            first_announced=page.release_date.isoformat() if page.release_date else None,
        )

        # Link content to feature
        db.add_content_feature_ref(
            content_id=content_id,
            feature_id=feature_id,
            feature_option_id=option_id,
            mention_type='announces',
        )

        new_feature_names.append(feature.name)
        processed_count += 1

    return (is_new_page, new_feature_names)


def _match_feature_id(category: str, name: str, features: dict) -> str:
    """Match a feature/category to a canonical feature_id.

    Args:
        category: Feature category from release notes.
        name: Feature name from release notes.
        features: CANVAS_FEATURES dictionary.

    Returns:
        Best matching feature_id, or 'general' if no match.
    """
    # Combine category and name for matching
    combined = f"{category} {name}".lower()

    # Direct name matches
    for feature_id, feature_name in features.items():
        if feature_name.lower() in combined or feature_id.lower() in combined:
            return feature_id

    # Category-based fallbacks
    category_lower = category.lower()
    if 'quiz' in category_lower:
        return 'new_quizzes' if 'new' in combined else 'classic_quizzes'
    if 'grade' in category_lower or 'speedgrader' in category_lower:
        return 'gradebook'
    if 'assignment' in category_lower:
        return 'assignments'
    if 'discussion' in category_lower:
        return 'discussions'
    if 'module' in category_lower:
        return 'modules'
    if 'page' in category_lower:
        return 'pages'
    if 'rubric' in category_lower:
        return 'rubrics'
    if 'calendar' in category_lower:
        return 'calendar'
    if 'inbox' in category_lower or 'conversation' in category_lower:
        return 'inbox'
    if 'studio' in category_lower:
        return 'canvas_studio'
    if 'mobile' in category_lower:
        return 'canvas_mobile'
    if 'api' in category_lower:
        return 'api'
    if 'lti' in category_lower or 'external' in category_lower:
        return 'external_apps_lti'
    if 'rce' in category_lower or 'rich content' in category_lower:
        return 'rich_content_editor'

    return 'general'


def classify_deploy_changes(
    page: DeployNotePage,
    db: "Database",
    first_run_limit: int = 3
) -> Tuple[bool, List[str]]:
    """Classify deploy note changes as new or existing.

    Creates feature_options records for deployed changes and links
    the content to features via content_feature_refs.

    Args:
        page: Parsed DeployNotePage with changes to classify.
        db: Database instance for tracking.
        first_run_limit: Max changes to include on first run.

    Returns:
        Tuple of (is_new_page, new_change_names):
        - is_new_page: True if this deploy note page is new
        - new_change_names: List of newly deployed change names
    """
    from src.constants import CANVAS_FEATURES

    if not page or not page.changes:
        return (False, [])

    # Generate content_id from the page URL
    content_id = extract_source_id(page.url, "deploy_note")

    # Check if this page is already tracked
    is_new_page = not db.item_exists(content_id)

    new_change_names: List[str] = []
    processed_count = 0

    for change in page.changes:
        # Apply first_run_limit for new pages
        if is_new_page and processed_count >= first_run_limit:
            break

        # Generate option_id from anchor_id or name
        option_id = change.anchor_id if change.anchor_id else \
            change.name.lower().replace(' ', '_').replace('-', '_')[:50]

        # Try to match to canonical feature based on category/name
        feature_id = _match_feature_id(change.category, change.name, CANVAS_FEATURES)

        # Create/update feature option record
        # Deploy notes typically represent released changes
        db.upsert_feature_option(
            option_id=option_id,
            feature_id=feature_id,
            name=change.name,
            status='released',  # Deploy notes announce released changes
            summary=None,
            config_level=None,
            default_state=None,
            first_announced=page.deploy_date.isoformat() if page.deploy_date else None,
        )

        # Link content to feature
        db.add_content_feature_ref(
            content_id=content_id,
            feature_id=feature_id,
            feature_option_id=option_id,
            mention_type='announces',
        )

        new_change_names.append(change.name)
        processed_count += 1

    return (is_new_page, new_change_names)
