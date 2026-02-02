"""RSS feed generation using feedgen."""

import logging
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from pathlib import Path

from feedgen.feed import FeedGenerator

from processor.content_processor import ContentItem, format_availability

if TYPE_CHECKING:
    from scrapers.instructure_community import ReleaseNotePage, DeployNotePage

logger = logging.getLogger("canvas_rss")

# Source labels for title formatting
SOURCE_LABELS = {
    "question": "Question Forum",
    "blog": "Blog",
    "release_note": "Release Notes",
    "deploy_note": "Deploy Notes",
}


def build_discussion_title(post_type: str, title: str, is_new: bool) -> str:
    """Build title with [NEW]/[UPDATE] badge and optional source label.

    Args:
        post_type: 'question', 'blog', 'release_note', or 'deploy_note'.
        title: Original post title.
        is_new: True for [NEW], False for [UPDATE].

    Returns:
        Formatted title string.
    """
    badge = "[NEW]" if is_new else "[UPDATE]"

    if post_type in ("question", "blog"):
        source = SOURCE_LABELS.get(post_type, "")
        return f"{badge} - {source} - {title}"
    else:
        return f"{badge} {title}"


# Section headers for discussion descriptions
SECTION_HEADERS = {
    "question_new": "NEW QUESTION",
    "question_update": "DISCUSSION UPDATE",
    "blog_new": "NEW BLOG POST",
    "blog_update": "BLOG UPDATE",
}


def format_discussion_description(
    post_type: str,
    is_new: bool,
    content: str,
    comment_count: int,
    previous_comment_count: int,
    new_comment_count: int,
    latest_comment: Optional[str]
) -> str:
    """Format RSS description for a discussion post.

    Returns:
        HTML-formatted description string.
    """
    from html import escape

    key = f"{post_type}_{'new' if is_new else 'update'}"
    header = SECTION_HEADERS.get(key, "UPDATE")

    parts = [f"<h3>{escape(header)}</h3>"]

    if is_new:
        truncated = content[:300] if len(content) > 300 else content
        if len(content) > 300:
            truncated = truncated.rsplit(' ', 1)[0] + "..."
        parts.append(f"<p>{escape(truncated)}</p>")
        parts.append(f"<p><em>Posted: {comment_count} comments</em></p>")
    else:
        parts.append(f"<p><strong>+{new_comment_count} new comments</strong> ({comment_count} total)</p>")

        if latest_comment:
            preview = latest_comment[:300]
            if len(latest_comment) > 300:
                preview = preview.rsplit(' ', 1)[0] + "..."
            parts.append("<p><strong>Latest reply:</strong></p>")
            parts.append(f'<blockquote>{escape(preview)}</blockquote>')

        parts.append("<hr/>")
        truncated = content[:200] if len(content) > 200 else content
        if len(content) > 200:
            truncated = truncated.rsplit(' ', 1)[0] + "..."
        parts.append(f"<p><em>Original:</em> {escape(truncated)}</p>")

    return "\n".join(parts)


def _extract_text_from_html(html_content: str, max_length: int = 200) -> str:
    """Extract plain text from HTML and truncate.

    Args:
        html_content: Raw HTML string.
        max_length: Maximum length for the output text.

    Returns:
        Plain text, truncated at word boundary if needed.
    """
    if not html_content:
        return ""
    try:
        from bs4 import BeautifulSoup
        text = BeautifulSoup(html_content, 'html.parser').get_text(separator=' ', strip=True)
        if len(text) > max_length:
            # Truncate at word boundary
            truncated = text[:max_length].rsplit(' ', 1)[0]
            return truncated + "..."
        return text
    except Exception:
        # Fallback: basic HTML stripping
        import re
        text = re.sub(r'<[^>]+>', ' ', html_content)
        text = ' '.join(text.split())  # Normalize whitespace
        if len(text) > max_length:
            truncated = text[:max_length].rsplit(' ', 1)[0]
            return truncated + "..."
        return text


def build_release_note_entry(
    page: "ReleaseNotePage",
    is_update: bool,
    new_features: Optional[List[str]] = None
) -> str:
    """Build RSS description for a release notes page.

    Args:
        page: ReleaseNotePage with parsed features.
        is_update: True if this is an update (new features added).
        new_features: List of anchor_ids for new features (updates only).

    Returns:
        HTML-formatted description string.
    """
    from html import escape

    parts = [f'<p><a href="{escape(page.url)}">Full Release Notes</a></p>']

    # Filter features if update
    features_to_show = page.features
    if is_update and new_features:
        features_to_show = [f for f in page.features if f.anchor_id in new_features]

    # Group by section
    for section_name, section_features in page.sections.items():
        if is_update and new_features:
            section_features = [f for f in section_features if f.anchor_id in new_features]
        if not section_features:
            continue

        parts.append(f"<h3>{escape(section_name.upper())}</h3>")
        parts.append("<ul>")

        for feature in section_features:
            anchor_link = f"{page.url}#{feature.anchor_id}"
            added_tag = ""
            if feature.added_date:
                added_tag = f' <em>[Added {feature.added_date.strftime("%Y-%m-%d")}]</em>'

            # Build feature list item
            feature_html = f'<li><strong>{escape(feature.category)}</strong> - '
            feature_html += f'<a href="{escape(anchor_link)}">{escape(feature.name)}</a>{added_tag}'

            # Task 14: Use feature.summary if available, otherwise extract text from raw_content
            if hasattr(feature, 'summary') and feature.summary:
                feature_html += f'<br/>{escape(feature.summary)}'
            else:
                # Fallback: extract and truncate text from raw HTML content
                summary_text = _extract_text_from_html(feature.raw_content)
                if summary_text:
                    feature_html += f'<br/>{escape(summary_text)}'
                else:
                    feature_html += '<br/>See link for details.'

            availability = format_availability(feature.table_data)
            feature_html += f'<br/><small><em>Availability: {escape(availability)}</em></small>'
            feature_html += '</li>'

            parts.append(feature_html)

        parts.append("</ul>")

    return "\n".join(parts)


# Status flags for deploy notes
STATUS_FLAGS = {
    "delayed": "⏸️",
}


def build_deploy_note_entry(
    page: "DeployNotePage",
    is_update: bool,
    new_changes: Optional[List[str]] = None
) -> str:
    """Build RSS description for a deploy notes page.

    Args:
        page: DeployNotePage with parsed changes.
        is_update: True if this is an update.
        new_changes: List of anchor_ids for new changes (updates only).

    Returns:
        HTML-formatted description string.
    """
    from html import escape

    parts = [f'<p><a href="{escape(page.url)}">Full Deploy Notes</a></p>']

    if page.beta_date:
        parts.append(f'<p><strong>Beta:</strong> {page.beta_date.strftime("%Y-%m-%d")} | <strong>Production:</strong> {page.deploy_date.strftime("%Y-%m-%d")}</p>')

    for section_name, section_changes in page.sections.items():
        if is_update and new_changes:
            section_changes = [c for c in section_changes if c.anchor_id in new_changes]
        if not section_changes:
            continue

        parts.append(f"<h3>{escape(section_name.upper())}</h3>")
        parts.append("<ul>")

        for change in section_changes:
            anchor_link = f"{page.url}#{change.anchor_id}"
            status_icon = "⏸️ " if change.status == "delayed" else ""

            # Build change list item
            change_html = f'<li>{status_icon}<strong>{escape(change.category)}</strong> - '
            change_html += f'<a href="{escape(anchor_link)}">{escape(change.name)}</a>'

            # Use change.summary if available, otherwise extract text from raw_content
            if hasattr(change, 'summary') and change.summary:
                change_html += f'<br/>{escape(change.summary)}'
            else:
                # Fallback: extract and truncate text from raw HTML content
                summary_text = _extract_text_from_html(change.raw_content)
                if summary_text:
                    change_html += f'<br/>{escape(summary_text)}'
                else:
                    change_html += '<br/>See link for details.'

            availability = format_availability(change.table_data)
            change_html += f'<br/><small><em>Availability: {escape(availability)}</em></small>'

            if change.status == "delayed" and change.status_date:
                change_html += f'<br/><small><strong>Delayed:</strong> {change.status_date.strftime("%Y-%m-%d")}</small>'

            change_html += '</li>'
            parts.append(change_html)

        parts.append("</ul>")

    return "\n".join(parts)


class RSSBuilder:
    """Generate RSS feed from processed content."""

    # Emoji prefixes for different sources
    SOURCE_EMOJIS = {
        "community": "\U0001F4E2",  # Megaphone
        "reddit": "\U0001F4AC",     # Speech bubble
        "status": "\U0001F527",     # Wrench
    }

    # Source badges for title prefixes (feature-centric view)
    SOURCE_BADGES = {
        "community": "[\U0001F4E2 Community]",
        "reddit": "[\U0001F4AC Reddit]",
        "status": "[\U0001F527 Status]",
    }

    # Content type badges for distinguishing Release Notes, Deploy Notes, etc.
    CONTENT_TYPE_BADGES = {
        "release_note": "[New]",
        "deploy_note": "[Fix]",
        "changelog": "[API]",
        "blog": "[Blog]",
        "blog_updated": "[Blog Update]",
        "question": "[Q&A]",
        "question_updated": "[Q&A Update]",
        "reddit": "",  # Reddit uses source badge instead
        "status": "",  # Status uses source badge instead
    }

    # Content type order for sorting (lower = higher priority)
    CONTENT_TYPE_ORDER = {
        "release_note": 1,
        "deploy_note": 2,
        "changelog": 3,
        "blog": 4,
        "blog_updated": 4,  # Same priority as blog
        "question": 5,
        "question_updated": 5,  # Same priority as question
        "reddit": 6,
        "status": 7,
    }

    # Category mapping for different sources
    SOURCE_CATEGORIES = {
        "community": "Release Notes",
        "reddit": "Community",
        "status": "Status",
    }

    # Human-readable names for content types (used in RSS description)
    CONTENT_TYPE_NAMES = {
        "release_note": "Release Notes",
        "deploy_note": "Deploy Notes",
        "changelog": "API Changelog",
        "blog": "Canvas LMS Blog",
        "blog_updated": "Canvas LMS Blog (Discussion Update)",
        "question": "Canvas LMS Question Forum",
        "question_updated": "Canvas LMS Question Forum (Discussion Update)",
        "reddit": "Reddit Community",
        "status": "Canvas Status",
    }

    # Priority for sorting by topic (lower number = higher priority)
    TOPIC_PRIORITY = {
        "Gradebook": 1,
        "Assignments": 2,
        "SpeedGrader": 3,
        "Quizzes": 4,
        "Discussions": 5,
        "Pages": 6,
        "Files": 7,
        "People": 8,
        "Groups": 9,
        "Calendar": 10,
        "Notifications": 11,
        "Mobile": 12,
        "API": 13,
        "Performance": 14,
        "Accessibility": 15,
        "General": 99,  # Fallback for unclassified items
    }

    # Legacy: Priority for sorting by source (lower number = higher priority)
    SOURCE_PRIORITY = {
        "community": 1,
        "status": 2,
        "reddit": 3,
    }

    def __init__(
        self,
        title: str = "Canvas LMS Daily Digest",
        link: str = "https://example.com/canvas-digest",
        description: str = "Daily digest of Canvas LMS updates, community feedback, and discussions"
    ):
        """Initialize the RSS builder.

        Args:
            title: Feed title
            link: Feed link URL
            description: Feed description
        """
        self.title = title
        self.link = link
        self.description = description

        # Initialize feedgen FeedGenerator
        self.fg = FeedGenerator()
        self.fg.title(title)
        self.fg.link(href=link, rel="alternate")
        self.fg.description(description)
        self.fg.language("en-us")
        self.fg.lastBuildDate(datetime.now(timezone.utc))

        logger.debug(f"RSSBuilder initialized with title: {title}")

    def _get_emoji_prefix(self, source: str) -> str:
        """Get emoji prefix for a given source.

        Args:
            source: Content source ('community', 'reddit', 'status')

        Returns:
            Emoji string or empty string if source not recognized
        """
        return self.SOURCE_EMOJIS.get(source.lower(), "")

    def _get_category(self, source: str) -> str:
        """Get category for a given source.

        Args:
            source: Content source ('community', 'reddit', 'status')

        Returns:
            Category string
        """
        return self.SOURCE_CATEGORIES.get(source.lower(), "General")

    def _format_title_with_badge(self, item: ContentItem) -> str:
        """Format title with topic, content type, and source badge for feature-centric view.

        Format: "Topic - [Latest] [ContentType] Title"
        Example: "Gradebook - [Latest] [New] Canvas Release Notes (2026-01-17)"

        Args:
            item: ContentItem to format

        Returns:
            Formatted title string
        """
        # Get primary topic (fallback to General)
        primary_topic = getattr(item, 'primary_topic', '') or "General"

        # Tracked items already have complete titles with [NEW]/[UPDATE] badges
        if getattr(item, 'has_tracking_badge', False):
            return item.title  # Use as-is, no modification

        # Check for "Latest" badge (only for release/deploy notes)
        is_latest = getattr(item, 'is_latest', False)
        latest_badge = "[Latest] " if is_latest else ""

        # Get content type badge (e.g., [New], [Fix], [API])
        content_type = getattr(item, 'content_type', '') or ""
        type_badge = self.CONTENT_TYPE_BADGES.get(content_type, "")

        # Get source badge (only for types that don't have their own badge)
        source_badge = self.SOURCE_BADGES.get(item.source.lower(), "")

        # Combine badges: prefer content type badge, fall back to source badge
        if type_badge:
            badges = type_badge
        elif source_badge:
            badges = source_badge
        else:
            badges = ""

        # Format: "Topic - [Latest] [Badge(s)] Title"
        if badges:
            return f"{primary_topic} - {latest_badge}{badges} {item.title}"
        else:
            return f"{primary_topic} - {latest_badge}{item.title}"

    def _format_description(self, item: ContentItem) -> str:
        """Format item description with summary, sentiment, topics, and source.

        For Tracked discussion items (has_tracking_badge=True), builds description
        from LLM summary + metadata. Otherwise falls back to legacy HTML format.

        Args:
            item: ContentItem to format

        Returns:
            HTML-formatted description string for CDATA
        """
        from html import escape

        # Tracked discussion items: build description from metadata + LLM summary
        if item.has_tracking_badge and item.content_type in ("question", "blog"):
            return self._format_tracked_discussion_description(item)

        # Tracked items with pre-formatted structured descriptions (release/deploy notes)
        if item.structured_description:
            return item.structured_description

        # Legacy format for non-tracked items (Reddit, Status, etc.)
        parts = []

        # Summary section
        summary = item.summary if item.summary else item.content[:500] if item.content else ""
        if summary:
            parts.append(f"<h3>Summary</h3>\n<p>{escape(summary)}</p>")

        # Sentiment section
        if item.sentiment:
            parts.append(f"<h3>Sentiment</h3>\n<p>{escape(item.sentiment)}</p>")

        # Source section - use content_type for accurate labeling
        content_type = getattr(item, 'content_type', '') or ''
        source_name = self.CONTENT_TYPE_NAMES.get(content_type, item.source.title())
        parts.append(f"<h3>Source</h3>\n<p>{escape(source_name)}</p>")

        # Topics section (secondary topics)
        if item.topics:
            topic_tags = " ".join(f"#{topic}" for topic in item.topics)
            parts.append(f"<h3>Related Topics</h3>\n<p>Tags: {escape(topic_tags)}</p>")

        return "\n\n".join(parts) if parts else ""

    def _format_tracked_discussion_description(self, item: ContentItem) -> str:
        """Format description for tracked discussion posts using LLM summary.

        Args:
            item: ContentItem with tracking metadata

        Returns:
            HTML-formatted description string
        """
        from html import escape

        key = f"{item.content_type}_{'new' if item.is_new_post else 'update'}"
        header = SECTION_HEADERS.get(key, "UPDATE")

        parts = [f"<h3>{escape(header)}</h3>"]

        # Use LLM summary if available, otherwise truncate raw content
        if item.summary:
            summary_text = item.summary
        else:
            summary_text = item.content[:300] if item.content else ""
            if len(item.content or "") > 300:
                summary_text = summary_text.rsplit(' ', 1)[0] + "..."

        if item.is_new_post:
            parts.append(f"<p>{escape(summary_text)}</p>")
            parts.append(f"<p><em>Posted: {item.comment_count} comments</em></p>")
        else:
            parts.append(f"<p><strong>+{item.new_comment_count} new comments</strong> ({item.comment_count} total)</p>")

            if item.latest_comment_preview:
                preview = item.latest_comment_preview[:300]
                if len(item.latest_comment_preview) > 300:
                    preview = preview.rsplit(' ', 1)[0] + "..."
                parts.append("<p><strong>Latest reply:</strong></p>")
                parts.append(f'<blockquote>{escape(preview)}</blockquote>')

            parts.append("<hr/>")
            # For updates, show summary of original post
            parts.append(f"<p><em>Summary:</em> {escape(summary_text)}</p>")

        # Add sentiment if available
        if item.sentiment and item.sentiment != "neutral":
            parts.append(f"<p><em>Sentiment: {escape(item.sentiment)}</em></p>")

        return "\n".join(parts)

    def add_item(self, item: ContentItem) -> None:
        """Add individual item to feed.

        Args:
            item: ContentItem to add to the feed
        """
        if not item:
            logger.warning("Attempted to add None item to feed, skipping")
            return

        # Create feed entry
        entry = self.fg.add_entry()

        # Set title with topic and source badge (feature-centric format)
        title = self._format_title_with_badge(item)
        entry.title(title)

        # Set link
        if item.url:
            entry.link(href=item.url)
        else:
            logger.warning(f"Item '{item.title}' has no URL")

        # Set description with CDATA content
        description = self._format_description(item)
        if description:
            entry.description(description)

        # Set pubDate
        if item.published_date:
            if isinstance(item.published_date, datetime):
                # Ensure timezone-aware datetime
                if item.published_date.tzinfo is None:
                    pub_date = item.published_date.replace(tzinfo=timezone.utc)
                else:
                    pub_date = item.published_date
            else:
                # Try to parse string date
                try:
                    pub_date = datetime.fromisoformat(str(item.published_date).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pub_date = datetime.now(timezone.utc)
                    logger.warning(f"Could not parse published_date for '{item.title}', using current time")
            entry.pubDate(pub_date)
        else:
            entry.pubDate(datetime.now(timezone.utc))

        # Set primary category based on topic (feature-centric)
        primary_topic = getattr(item, 'primary_topic', '') or "General"
        entry.category(term=primary_topic)

        # Add source as secondary category
        source_category = self._get_category(item.source)
        entry.category(term=source_category)

        # Add secondary topics as additional categories
        if item.topics:
            for topic in item.topics:
                entry.category(term=topic)

        # Set unique ID using source_id if available
        if item.source_id:
            entry.guid(f"{item.source}:{item.source_id}", permalink=False)
        elif item.url:
            entry.guid(item.url, permalink=True)

        logger.debug(f"Added item to feed: {title}")

    def create_feed(self, items: Optional[List[ContentItem]] = None) -> str:
        """Generate RSS 2.0 XML feed.

        Args:
            items: List of ContentItems to include in the feed

        Returns:
            RSS XML string
        """
        if items is None:
            items = []

        # Filter out None items
        items = [item for item in items if item is not None]

        if not items:
            logger.info("Creating feed with no items")
        else:
            # Sort items by:
            # 1. Topic priority (feature-centric) - Gradebook first, etc.
            # 2. Content type order - Release notes before deploy notes, etc.
            # 3. Date (most recent first) within each group
            #
            # Note: feedgen adds items in reverse order (last added = first in output)
            # So we sort descending (reverse=True) to get highest priority topics first
            sorted_items = sorted(
                items,
                key=lambda x: (
                    self.TOPIC_PRIORITY.get(getattr(x, 'primary_topic', '') or 'General', 99),
                    self.CONTENT_TYPE_ORDER.get(getattr(x, 'content_type', '') or '', 99),
                    -(x.published_date.timestamp() if x.published_date else 0)
                ),
                reverse=True
            )

            # Add each item to feed
            for item in sorted_items:
                try:
                    self.add_item(item)
                except Exception as e:
                    logger.error(f"Failed to add item '{getattr(item, 'title', 'Unknown')}': {e}")

            logger.info(f"Created feed with {len(sorted_items)} items")

        # Generate RSS XML
        rss_str = self.fg.rss_str(pretty=True)
        return rss_str.decode("utf-8")

    def save_feed(self, output_path: str) -> None:
        """Write RSS XML to file.

        Args:
            output_path: Path to write the RSS XML file
        """
        # Ensure parent directory exists
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Generate and write feed
        rss_content = self.fg.rss_str(pretty=True).decode("utf-8")
        path.write_text(rss_content, encoding="utf-8")

        logger.info(f"RSS feed saved to {output_path}")
