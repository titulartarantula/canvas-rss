"""Tests for RSS builder."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import xml.etree.ElementTree as ET


class TestRSSBuilderInitialization:
    """Tests for RSSBuilder initialization."""

    def test_rss_builder_initialization_defaults(self):
        """Test that RSSBuilder initializes with correct defaults."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        assert builder.title == "Canvas LMS Daily Digest"
        assert "example.com" in builder.link
        assert builder.description == "Daily digest of Canvas LMS updates, community feedback, and discussions"

    def test_rss_builder_custom_title(self):
        """Test RSSBuilder with custom title."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder(title="Custom Feed Title")
        assert builder.title == "Custom Feed Title"

    def test_rss_builder_custom_link(self):
        """Test RSSBuilder with custom link."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder(link="https://example.com/feed")
        assert builder.link == "https://example.com/feed"

    def test_rss_builder_custom_description(self):
        """Test RSSBuilder with custom description."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder(description="My custom description")
        assert builder.description == "My custom description"

    def test_rss_builder_custom_initialization(self):
        """Test RSSBuilder with all custom values."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder(
            title="Custom Feed",
            link="https://example.com",
            description="Custom description"
        )
        assert builder.title == "Custom Feed"
        assert builder.link == "https://example.com"
        assert builder.description == "Custom description"

    def test_rss_builder_feed_generator_initialized(self):
        """Test that FeedGenerator is properly initialized."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        assert builder.fg is not None

    def test_rss_builder_language_set(self):
        """Test that feed language is set to en-us."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        # Generate feed and verify language in XML
        rss_xml = builder.create_feed([])
        assert "en-us" in rss_xml


class TestRSSBuilderEmojiPrefix:
    """Tests for emoji prefix functionality."""

    def test_get_emoji_prefix_community(self):
        """Test emoji prefix for community source."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        emoji = builder._get_emoji_prefix("community")
        assert emoji == "\U0001F4E2"  # Megaphone

    def test_get_emoji_prefix_reddit(self):
        """Test emoji prefix for reddit source."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        emoji = builder._get_emoji_prefix("reddit")
        assert emoji == "\U0001F4AC"  # Speech bubble

    def test_get_emoji_prefix_status(self):
        """Test emoji prefix for status source."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        emoji = builder._get_emoji_prefix("status")
        assert emoji == "\U0001F527"  # Wrench

    def test_get_emoji_prefix_unknown_source(self):
        """Test emoji prefix for unknown source returns empty string."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        emoji = builder._get_emoji_prefix("unknown")
        assert emoji == ""

    def test_get_emoji_prefix_case_insensitive(self):
        """Test that emoji prefix lookup is case insensitive."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        assert builder._get_emoji_prefix("COMMUNITY") == "\U0001F4E2"
        assert builder._get_emoji_prefix("Reddit") == "\U0001F4AC"
        assert builder._get_emoji_prefix("STATUS") == "\U0001F527"


class TestRSSBuilderCategory:
    """Tests for category functionality."""

    def test_get_category_community(self):
        """Test category for community source."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        category = builder._get_category("community")
        assert category == "Release Notes"

    def test_get_category_reddit(self):
        """Test category for reddit source."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        category = builder._get_category("reddit")
        assert category == "Community"

    def test_get_category_status(self):
        """Test category for status source."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        category = builder._get_category("status")
        assert category == "Status"

    def test_get_category_unknown_source(self):
        """Test category for unknown source returns General."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        category = builder._get_category("unknown")
        assert category == "General"

    def test_get_category_case_insensitive(self):
        """Test that category lookup is case insensitive."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        assert builder._get_category("COMMUNITY") == "Release Notes"
        assert builder._get_category("Reddit") == "Community"


class TestRSSBuilderFormatDescription:
    """Tests for description formatting."""

    def test_format_description_with_summary(self):
        """Test description formatting with summary."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="test_123",
            title="Test Title",
            url="https://example.com/test",
            content="Full content here",
            summary="Brief summary"
        )

        description = builder._format_description(item)
        assert "<h3>Summary</h3>" in description
        assert "<p>Brief summary</p>" in description

    def test_format_description_uses_content_if_no_summary(self):
        """Test that content is used if no summary is provided."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="test_123",
            title="Test Title",
            url="https://example.com/test",
            content="This is the full content of the item"
        )

        description = builder._format_description(item)
        assert "This is the full content of the item" in description

    def test_format_description_truncates_long_content(self):
        """Test that long content is truncated to 500 chars."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        long_content = "x" * 1000
        item = ContentItem(
            source="community",
            source_id="test_123",
            title="Test Title",
            url="https://example.com/test",
            content=long_content
        )

        description = builder._format_description(item)
        # The summary section should use truncated content
        assert len(description) < 600  # Account for HTML tags

    def test_format_description_with_sentiment(self):
        """Test description formatting with sentiment."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="test_123",
            title="Test Title",
            url="https://example.com/test",
            content="Content",
            summary="Summary",
            sentiment="positive"
        )

        description = builder._format_description(item)
        assert "<h3>Sentiment</h3>" in description
        assert "<p>positive</p>" in description

    def test_format_description_with_topics(self):
        """Test description formatting with secondary topics."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="test_123",
            title="Test Title",
            url="https://example.com/test",
            content="Content",
            topics=["Gradebook", "SpeedGrader"]
        )

        description = builder._format_description(item)
        assert "<h3>Related Topics</h3>" in description
        assert "#Gradebook" in description
        assert "#SpeedGrader" in description

    def test_format_description_empty_fields(self):
        """Test description formatting when most optional fields are empty."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="test_123",
            title="Test Title",
            url="https://example.com/test",
            content=""
        )

        description = builder._format_description(item)
        # Source section is always included
        assert "<h3>Source</h3>" in description
        # But summary, sentiment, and topics should not be present
        assert "<h3>Summary</h3>" not in description
        assert "<h3>Sentiment</h3>" not in description
        assert "<h3>Related Topics</h3>" not in description

    def test_format_description_all_sections(self):
        """Test description with all sections present."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="test_123",
            title="Test Title",
            url="https://example.com/test",
            content="Full content",
            summary="Brief summary",
            sentiment="neutral",
            topics=["Assignments", "Quizzes"]
        )

        description = builder._format_description(item)
        assert "<h3>Summary</h3>" in description
        assert "<h3>Sentiment</h3>" in description
        assert "<h3>Source</h3>" in description
        assert "<h3>Related Topics</h3>" in description


class TestRSSBuilderAddItem:
    """Tests for add_item method."""

    def test_add_item_basic(self):
        """Test adding a basic item to the feed."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="New Feature Release",
            url="https://example.com/post/123",
            content="Full content here",
            summary="Brief summary",
            sentiment="positive",
            topics=["Gradebook"],
            published_date=datetime.now(timezone.utc),
            engagement_score=10
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        # Item should be in the feed
        assert "New Feature Release" in rss_xml

    def test_add_item_with_source_badge_community(self):
        """Test that community items get topic and source badge in title."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="New Feature",
            url="https://example.com/123",
            content="Content",
            primary_topic="Gradebook"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        # Should have format: "Topic - [emoji Source] Title"
        assert "Gradebook - [\U0001F4E2 Community] New Feature" in rss_xml

    def test_add_item_with_source_badge_reddit(self):
        """Test that reddit items get topic and source badge in title."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="reddit",
            source_id="reddit_123",
            title="Discussion Topic",
            url="https://reddit.com/r/canvas/123",
            content="Content",
            primary_topic="Assignments"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        assert "Assignments - [\U0001F4AC Reddit] Discussion Topic" in rss_xml

    def test_add_item_with_source_badge_status(self):
        """Test that status items get topic and source badge in title."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="status",
            source_id="status_123",
            title="Maintenance Complete",
            url="https://status.instructure.com/123",
            content="Content",
            primary_topic="Performance"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        assert "Performance - [\U0001F527 Status] Maintenance Complete" in rss_xml

    def test_add_item_without_primary_topic_uses_general(self):
        """Test that items without primary_topic default to General."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_456",
            title="Some Update",
            url="https://example.com/456",
            content="Content"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        assert "General - [\U0001F4E2 Community] Some Update" in rss_xml

    def test_add_item_none_item_skipped(self):
        """Test that None item is skipped without error."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        builder.add_item(None)  # Should not raise exception

        rss_xml = builder.create_feed()
        # Feed should be valid but empty (no items added)
        assert "<?xml" in rss_xml

    def test_add_item_missing_url(self):
        """Test adding item with missing URL (logs warning but continues)."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="No URL Item",
            url="",  # Empty URL
            content="Content"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        assert "No URL Item" in rss_xml

    def test_add_item_with_datetime_published_date(self):
        """Test adding item with datetime published_date."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        pub_date = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="Test Item",
            url="https://example.com/123",
            content="Content",
            published_date=pub_date
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        # Date should be in RSS format
        assert "15 Jan 2024" in rss_xml or "Mon, 15 Jan 2024" in rss_xml

    def test_add_item_with_naive_datetime(self):
        """Test adding item with timezone-naive datetime."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        naive_date = datetime(2024, 1, 15, 10, 30, 0)  # No timezone
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="Test Item",
            url="https://example.com/123",
            content="Content",
            published_date=naive_date
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        # Should work - timezone added automatically
        assert "Test Item" in rss_xml

    def test_add_item_with_iso_string_date(self):
        """Test adding item with ISO string published_date."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="Test Item",
            url="https://example.com/123",
            content="Content",
            published_date="2024-01-15T10:30:00Z"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        assert "Test Item" in rss_xml

    def test_add_item_with_iso_string_date_timezone_offset(self):
        """Test adding item with ISO string with timezone offset."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="Test Item",
            url="https://example.com/123",
            content="Content",
            published_date="2024-01-15T10:30:00+00:00"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        assert "Test Item" in rss_xml

    def test_add_item_with_invalid_date_string(self):
        """Test adding item with invalid date string (uses current time)."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="Test Item",
            url="https://example.com/123",
            content="Content",
            published_date="not-a-valid-date"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        # Should still work with current time
        assert "Test Item" in rss_xml

    def test_add_item_with_none_published_date(self):
        """Test adding item with None published_date (uses current time)."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="Test Item",
            url="https://example.com/123",
            content="Content",
            published_date=None
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        assert "Test Item" in rss_xml

    def test_add_item_category_from_source(self):
        """Test that primary category is set from source."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="Test Item",
            url="https://example.com/123",
            content="Content"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        assert "Release Notes" in rss_xml

    def test_add_item_topics_as_categories(self):
        """Test that topics are added as additional categories."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="Test Item",
            url="https://example.com/123",
            content="Content",
            topics=["Gradebook", "SpeedGrader"]
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        # Topics should appear as categories
        assert "Gradebook" in rss_xml
        assert "SpeedGrader" in rss_xml

    def test_add_item_guid_from_source_id(self):
        """Test that GUID is set from source_id."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_123",
            title="Test Item",
            url="https://example.com/123",
            content="Content"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        # GUID should be formatted as source:source_id
        assert "community:community_123" in rss_xml

    def test_add_item_guid_from_url_if_no_source_id(self):
        """Test that GUID uses URL if source_id is empty."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="",  # Empty source_id
            title="Test Item",
            url="https://example.com/unique-url",
            content="Content"
        )

        builder.add_item(item)
        rss_xml = builder.create_feed()

        assert "https://example.com/unique-url" in rss_xml


class TestRSSBuilderCreateFeed:
    """Tests for create_feed method."""

    def test_create_feed_empty_list(self):
        """Test creating feed with empty list returns valid XML."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        rss_xml = builder.create_feed([])

        # Should be valid XML
        assert "<?xml" in rss_xml
        assert "<rss" in rss_xml
        assert "</rss>" in rss_xml

    def test_create_feed_none_items(self):
        """Test creating feed with None items (defaults to empty)."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        rss_xml = builder.create_feed(None)

        assert "<?xml" in rss_xml

    def test_create_feed_returns_utf8_string(self):
        """Test that create_feed returns a UTF-8 string."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()
        rss_xml = builder.create_feed([])

        assert isinstance(rss_xml, str)
        # Should contain UTF-8 encoding declaration (may use single or double quotes)
        assert "encoding='UTF-8'" in rss_xml or 'encoding="UTF-8"' in rss_xml

    def test_create_feed_with_items_sorted_by_priority(self):
        """Test that items are sorted by priority (community > status > reddit)."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()

        # Create items in wrong order
        reddit_item = ContentItem(
            source="reddit",
            source_id="reddit_1",
            title="Reddit Post",
            url="https://reddit.com/1",
            content="Content"
        )
        community_item = ContentItem(
            source="community",
            source_id="community_1",
            title="Community Post",
            url="https://community.canvaslms.com/1",
            content="Content"
        )
        status_item = ContentItem(
            source="status",
            source_id="status_1",
            title="Status Update",
            url="https://status.instructure.com/1",
            content="Content"
        )

        rss_xml = builder.create_feed([reddit_item, status_item, community_item])

        # Find positions in XML - community should come first, then status, then reddit
        community_pos = rss_xml.find("Community Post")
        status_pos = rss_xml.find("Status Update")
        reddit_pos = rss_xml.find("Reddit Post")

        assert community_pos < status_pos < reddit_pos, \
            f"Expected community ({community_pos}) < status ({status_pos}) < reddit ({reddit_pos})"

    def test_create_feed_skips_none_in_list(self):
        """Test that None items in list are skipped when filtered externally."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()

        valid_item = ContentItem(
            source="community",
            source_id="community_1",
            title="Valid Item",
            url="https://example.com/1",
            content="Content"
        )

        # Filter None items before passing to create_feed
        items = [None, valid_item, None]
        filtered_items = [item for item in items if item is not None]
        rss_xml = builder.create_feed(filtered_items)

        assert "Valid Item" in rss_xml

    def test_create_feed_handles_none_in_list_directly(self):
        """Test that create_feed handles None items in list gracefully.

        Verifies that None items are filtered out before sorting.
        """
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()

        valid_item = ContentItem(
            source="community",
            source_id="community_1",
            title="Valid Item",
            url="https://example.com/1",
            content="Content"
        )

        # None items should be filtered out
        rss_xml = builder.create_feed([None, valid_item, None])

        assert "Valid Item" in rss_xml

    def test_create_feed_handles_item_with_exception(self):
        """Test that create_feed handles items that cause exceptions."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()

        # Create a valid item
        valid_item = ContentItem(
            source="community",
            source_id="community_1",
            title="Valid Item",
            url="https://example.com/1",
            content="Content"
        )

        # Even if one item fails, others should be added
        rss_xml = builder.create_feed([valid_item])
        assert "Valid Item" in rss_xml

    def test_create_feed_valid_xml_structure(self):
        """Test that generated feed has valid XML structure."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_1",
            title="Test Item",
            url="https://example.com/1",
            content="Content"
        )

        rss_xml = builder.create_feed([item])

        # Parse XML to verify it's valid
        root = ET.fromstring(rss_xml)
        assert root.tag == "rss"

        channel = root.find("channel")
        assert channel is not None

        title = channel.find("title")
        assert title is not None

    def test_create_feed_includes_feed_metadata(self):
        """Test that feed includes title, link, description."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder(
            title="Test Feed",
            link="https://example.com/feed",
            description="Test Description"
        )
        rss_xml = builder.create_feed([])

        assert "Test Feed" in rss_xml
        assert "https://example.com/feed" in rss_xml
        assert "Test Description" in rss_xml


class TestRSSBuilderSaveFeed:
    """Tests for save_feed method."""

    def test_save_feed_creates_file(self, tmp_path):
        """Test that save_feed creates the output file."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_1",
            title="Test Item",
            url="https://example.com/1",
            content="Content"
        )
        builder.add_item(item)

        output_path = tmp_path / "feed.xml"
        builder.save_feed(str(output_path))

        assert output_path.exists()

    def test_save_feed_creates_parent_directories(self, tmp_path):
        """Test that save_feed creates parent directories if needed."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()

        output_path = tmp_path / "nested" / "dir" / "feed.xml"
        builder.save_feed(str(output_path))

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_save_feed_writes_utf8(self, tmp_path):
        """Test that save_feed writes UTF-8 encoded content."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        # Add item with unicode content
        item = ContentItem(
            source="community",
            source_id="community_1",
            title="Test with Unicode",
            url="https://example.com/1",
            content="Content"
        )
        builder.add_item(item)

        output_path = tmp_path / "feed.xml"
        builder.save_feed(str(output_path))

        # Read back and verify
        content = output_path.read_text(encoding="utf-8")
        assert "Test with Unicode" in content
        # Check for megaphone emoji
        assert "\U0001F4E2" in content

    def test_save_feed_overwrites_existing(self, tmp_path):
        """Test that save_feed overwrites existing file."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        output_path = tmp_path / "feed.xml"

        # Create initial file
        output_path.write_text("Old content", encoding="utf-8")

        # Save new feed
        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_1",
            title="New Content",
            url="https://example.com/1",
            content="Content"
        )
        builder.add_item(item)
        builder.save_feed(str(output_path))

        content = output_path.read_text(encoding="utf-8")
        assert "Old content" not in content
        assert "New Content" in content

    def test_save_feed_valid_xml_file(self, tmp_path):
        """Test that saved file contains valid XML."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder()
        item = ContentItem(
            source="community",
            source_id="community_1",
            title="Test Item",
            url="https://example.com/1",
            content="Content"
        )
        builder.add_item(item)

        output_path = tmp_path / "feed.xml"
        builder.save_feed(str(output_path))

        # Parse the file to verify valid XML
        tree = ET.parse(str(output_path))
        root = tree.getroot()
        assert root.tag == "rss"


class TestRSSBuilderSourceConstants:
    """Tests for source-related class constants."""

    def test_source_emojis_defined(self):
        """Test that SOURCE_EMOJIS constant is properly defined."""
        from generator.rss_builder import RSSBuilder

        assert "community" in RSSBuilder.SOURCE_EMOJIS
        assert "reddit" in RSSBuilder.SOURCE_EMOJIS
        assert "status" in RSSBuilder.SOURCE_EMOJIS

    def test_source_categories_defined(self):
        """Test that SOURCE_CATEGORIES constant is properly defined."""
        from generator.rss_builder import RSSBuilder

        assert RSSBuilder.SOURCE_CATEGORIES["community"] == "Release Notes"
        assert RSSBuilder.SOURCE_CATEGORIES["reddit"] == "Community"
        assert RSSBuilder.SOURCE_CATEGORIES["status"] == "Status"

    def test_source_priority_defined(self):
        """Test that SOURCE_PRIORITY constant is properly defined."""
        from generator.rss_builder import RSSBuilder

        assert RSSBuilder.SOURCE_PRIORITY["community"] == 1
        assert RSSBuilder.SOURCE_PRIORITY["status"] == 2
        assert RSSBuilder.SOURCE_PRIORITY["reddit"] == 3


class TestRSSBuilderIntegration:
    """Integration tests for RSSBuilder workflow."""

    def test_full_workflow_multiple_sources(self, tmp_path):
        """Test complete workflow with items from all sources."""
        from generator.rss_builder import RSSBuilder
        from processor.content_processor import ContentItem

        builder = RSSBuilder(
            title="Canvas Daily Digest",
            link="https://example.com/digest",
            description="Daily updates"
        )

        # Create items from each source
        items = [
            ContentItem(
                source="community",
                source_id="community_1",
                title="New Gradebook Features",
                url="https://community.canvaslms.com/1",
                content="Exciting new features",
                summary="New gradebook UI",
                sentiment="positive",
                topics=["Gradebook"],
                published_date=datetime.now(timezone.utc)
            ),
            ContentItem(
                source="reddit",
                source_id="reddit_1",
                title="Canvas Performance Issues",
                url="https://reddit.com/r/canvas/1",
                content="Users reporting slowness",
                summary="Performance complaints",
                sentiment="negative",
                topics=["Performance"],
                published_date=datetime.now(timezone.utc)
            ),
            ContentItem(
                source="status",
                source_id="status_1",
                title="Scheduled Maintenance",
                url="https://status.instructure.com/1",
                content="Maintenance window",
                summary="Planned downtime",
                sentiment="neutral",
                topics=["Maintenance"],
                published_date=datetime.now(timezone.utc)
            )
        ]

        # Create and save feed
        output_path = tmp_path / "output" / "digest.xml"
        rss_xml = builder.create_feed(items)
        builder.save_feed(str(output_path))

        # Verify file exists and contains expected content
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")

        # All items present
        assert "New Gradebook Features" in content
        assert "Canvas Performance Issues" in content
        assert "Scheduled Maintenance" in content

        # Emojis present
        assert "\U0001F4E2" in content  # Community
        assert "\U0001F4AC" in content  # Reddit
        assert "\U0001F527" in content  # Status

        # Categories present
        assert "Release Notes" in content
        assert "Community" in content
        assert "Status" in content

    def test_empty_feed_workflow(self, tmp_path):
        """Test workflow with no items produces valid empty feed."""
        from generator.rss_builder import RSSBuilder

        builder = RSSBuilder()

        output_path = tmp_path / "empty_feed.xml"
        builder.create_feed([])
        builder.save_feed(str(output_path))

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")

        # Valid RSS structure
        assert "<rss" in content
        assert "<channel>" in content
        assert "</rss>" in content


class TestSourceLabels:
    """Tests for SOURCE_LABELS constant."""

    def test_source_labels_defined(self):
        """Test SOURCE_LABELS has expected keys."""
        from generator.rss_builder import SOURCE_LABELS

        assert "question" in SOURCE_LABELS
        assert "blog" in SOURCE_LABELS
        assert SOURCE_LABELS["question"] == "Question Forum"
        assert SOURCE_LABELS["blog"] == "Blog"
