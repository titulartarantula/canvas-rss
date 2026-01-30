"""RSS feed generation using feedgen."""

import logging
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path

from feedgen.feed import FeedGenerator

from src.processor.content_processor import ContentItem

logger = logging.getLogger("canvas_rss")


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

    # Category mapping for different sources
    SOURCE_CATEGORIES = {
        "community": "Release Notes",
        "reddit": "Community",
        "status": "Status",
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
        link: str = "https://drwhom.ca/canvas-digest",
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
        """Format title with topic and source badge for feature-centric view.

        Format: "Topic - [Source Badge] Title"
        Example: "Gradebook - [📢 Community] New weighted grading option"

        Args:
            item: ContentItem to format

        Returns:
            Formatted title string
        """
        # Get primary topic (fallback to General)
        primary_topic = getattr(item, 'primary_topic', '') or "General"

        # Get source badge
        badge = self.SOURCE_BADGES.get(item.source.lower(), "")

        # Format: "Topic - [Badge] Title"
        if badge:
            return f"{primary_topic} - {badge} {item.title}"
        else:
            return f"{primary_topic} - {item.title}"

    def _format_description(self, item: ContentItem) -> str:
        """Format item description with summary, sentiment, topics, and source.

        Args:
            item: ContentItem to format

        Returns:
            HTML-formatted description string for CDATA
        """
        parts = []

        # Summary section
        summary = item.summary if item.summary else item.content[:500] if item.content else ""
        if summary:
            parts.append(f"<h3>Summary</h3>\n<p>{summary}</p>")

        # Sentiment section
        if item.sentiment:
            parts.append(f"<h3>Sentiment</h3>\n<p>{item.sentiment}</p>")

        # Source section
        source_name = self.SOURCE_CATEGORIES.get(item.source.lower(), item.source)
        parts.append(f"<h3>Source</h3>\n<p>{source_name}</p>")

        # Topics section (secondary topics)
        if item.topics:
            topic_tags = " ".join(f"#{topic}" for topic in item.topics)
            parts.append(f"<h3>Related Topics</h3>\n<p>Tags: {topic_tags}</p>")

        return "\n\n".join(parts) if parts else ""

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
            # Sort items by topic priority (feature-centric), then by date within each topic
            # Note: feedgen adds items in reverse order (last added = first in output)
            # So we sort descending by topic priority (reverse=True) to get highest priority topics first
            # Within each topic, we sort by date (most recent first)
            sorted_items = sorted(
                items,
                key=lambda x: (
                    self.TOPIC_PRIORITY.get(getattr(x, 'primary_topic', '') or 'General', 99),
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
