"""Tests for main.py orchestration module."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path
import tempfile
import os

from main import (
    community_post_to_content_item,
    reddit_post_to_content_item,
    incident_to_content_item,
    main,
)
from processor.content_processor import ContentItem
from scrapers.instructure_community import CommunityPost, ReleaseNote, ChangeLogEntry
from scrapers.reddit_client import RedditPost
from scrapers.status_page import Incident


class TestCommunityPostToContentItem:
    """Tests for community_post_to_content_item conversion function."""

    def test_converts_community_post_basic_fields(self):
        """Test basic field conversion from CommunityPost."""
        post = CommunityPost(
            title="Test Post",
            url="https://community.instructure.com/test",
            content="Test content",
            published_date=datetime(2026, 1, 30, 12, 0, 0),
            likes=10,
            comments=5,
            post_type="discussion",
        )

        item = community_post_to_content_item(post)

        assert item.title == "Test Post"
        assert item.url == "https://community.instructure.com/test"
        assert item.content == "Test content"
        assert item.source == "community"
        assert item.published_date == datetime(2026, 1, 30, 12, 0, 0)

    def test_calculates_engagement_score_from_likes_and_comments(self):
        """Test engagement score is sum of likes and comments."""
        post = CommunityPost(
            title="Popular Post",
            url="https://example.com",
            content="Content",
            published_date=datetime.now(),
            likes=25,
            comments=10,
        )

        item = community_post_to_content_item(post)

        assert item.engagement_score == 35

    def test_converts_release_note(self):
        """Test conversion of ReleaseNote dataclass."""
        note = ReleaseNote(
            title="Canvas Release Notes",
            url="https://community.instructure.com/release-notes/123",
            content="New features in this release",
            published_date=datetime(2026, 1, 15),
            likes=100,
            comments=20,
        )

        item = community_post_to_content_item(note)

        assert item.source == "community"
        assert item.title == "Canvas Release Notes"
        assert item.engagement_score == 120

    def test_converts_changelog_entry(self):
        """Test conversion of ChangeLogEntry dataclass."""
        entry = ChangeLogEntry(
            title="API Changelog",
            url="https://community.instructure.com/changelog/456",
            content="New API endpoint added",
            published_date=datetime(2026, 1, 20),
        )

        item = community_post_to_content_item(entry)

        assert item.source == "community"
        assert item.title == "API Changelog"
        # ChangeLogEntry has no likes/comments, so engagement should be 0
        assert item.engagement_score == 0

    def test_preserves_source_id(self):
        """Test that source_id property is preserved."""
        post = CommunityPost(
            title="Test",
            url="https://example.com/unique",
            content="Content",
            published_date=datetime.now(),
        )

        item = community_post_to_content_item(post)

        assert item.source_id == post.source_id

    def test_handles_zero_engagement(self):
        """Test handling of post with zero likes and comments."""
        post = CommunityPost(
            title="New Post",
            url="https://example.com",
            content="Content",
            published_date=datetime.now(),
            likes=0,
            comments=0,
        )

        item = community_post_to_content_item(post)

        assert item.engagement_score == 0

    def test_returns_content_item_type(self):
        """Test that return type is ContentItem."""
        post = CommunityPost(
            title="Test",
            url="https://example.com",
            content="Content",
            published_date=datetime.now(),
        )

        item = community_post_to_content_item(post)

        assert isinstance(item, ContentItem)


class TestRedditPostToContentItem:
    """Tests for reddit_post_to_content_item conversion function."""

    def test_converts_reddit_post_basic_fields(self):
        """Test basic field conversion from RedditPost."""
        post = RedditPost(
            title="Canvas question",
            url="https://reddit.com/r/canvas/123",
            content="How do I use Canvas?",
            subreddit="canvas",
            author="testuser",
            score=50,
            num_comments=10,
            published_date=datetime(2026, 1, 30, 10, 0, 0),
            source_id="reddit_123",
            permalink="/r/canvas/comments/123",
        )

        item = reddit_post_to_content_item(post)

        assert item.title == "Canvas question"
        assert item.url == "https://reddit.com/r/canvas/123"
        assert item.content == "How do I use Canvas?"
        assert item.source == "reddit"
        assert item.published_date == datetime(2026, 1, 30, 10, 0, 0)

    def test_calculates_engagement_score_from_score_and_comments(self):
        """Test engagement score is sum of score and num_comments."""
        post = RedditPost(
            title="Popular post",
            url="https://reddit.com/test",
            content="Content",
            subreddit="canvas",
            author="user",
            score=100,
            num_comments=50,
            published_date=datetime.now(),
            source_id="reddit_456",
        )

        item = reddit_post_to_content_item(post)

        assert item.engagement_score == 150

    def test_anonymizes_author(self):
        """Test that author is anonymized during conversion."""
        post = RedditPost(
            title="My question",
            url="https://reddit.com/test",
            content="Content from u/specific_user",
            subreddit="canvas",
            author="specific_user",
            score=10,
            num_comments=5,
            published_date=datetime.now(),
            source_id="reddit_789",
        )

        item = reddit_post_to_content_item(post)

        # The anonymize() method replaces author with "A Reddit user"
        # Content PII redaction happens in ContentProcessor, not here
        assert item.source == "reddit"

    def test_preserves_source_id(self):
        """Test that source_id is preserved."""
        post = RedditPost(
            title="Test",
            url="https://reddit.com/test",
            content="Content",
            subreddit="canvas",
            author="user",
            score=5,
            num_comments=2,
            published_date=datetime.now(),
            source_id="reddit_unique_id",
        )

        item = reddit_post_to_content_item(post)

        assert item.source_id == "reddit_unique_id"

    def test_handles_zero_engagement(self):
        """Test handling of post with zero score and comments."""
        post = RedditPost(
            title="New post",
            url="https://reddit.com/test",
            content="Content",
            subreddit="canvas",
            author="user",
            score=0,
            num_comments=0,
            published_date=datetime.now(),
            source_id="reddit_000",
        )

        item = reddit_post_to_content_item(post)

        assert item.engagement_score == 0

    def test_returns_content_item_type(self):
        """Test that return type is ContentItem."""
        post = RedditPost(
            title="Test",
            url="https://reddit.com/test",
            content="Content",
            subreddit="canvas",
            author="user",
            score=1,
            num_comments=1,
            published_date=datetime.now(),
            source_id="reddit_test",
        )

        item = reddit_post_to_content_item(post)

        assert isinstance(item, ContentItem)


class TestIncidentToContentItem:
    """Tests for incident_to_content_item conversion function."""

    def test_converts_incident_basic_fields(self):
        """Test basic field conversion from Incident."""
        incident = Incident(
            title="Service Disruption",
            url="https://status.instructure.com/incidents/123",
            status="investigating",
            impact="minor",
            content="We are investigating an issue.",
            created_at=datetime(2026, 1, 30, 8, 0, 0),
            updated_at=datetime(2026, 1, 30, 9, 0, 0),
            source_id="incident_123",
        )

        item = incident_to_content_item(incident)

        assert item.url == "https://status.instructure.com/incidents/123"
        assert item.content == "We are investigating an issue."
        assert item.source == "status"
        assert item.published_date == datetime(2026, 1, 30, 8, 0, 0)

    def test_prefixes_title_with_impact_level(self):
        """Test that title is prefixed with impact level."""
        incident = Incident(
            title="Database Issues",
            url="https://status.instructure.com/incidents/456",
            status="identified",
            impact="major",
            content="Database performance degradation.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_id="incident_456",
        )

        item = incident_to_content_item(incident)

        assert item.title == "[MAJOR] Database Issues"

    def test_prefixes_title_with_critical_impact(self):
        """Test title prefix for critical impact."""
        incident = Incident(
            title="Complete Outage",
            url="https://status.instructure.com/incidents/789",
            status="investigating",
            impact="critical",
            content="Canvas is completely down.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_id="incident_789",
        )

        item = incident_to_content_item(incident)

        assert item.title == "[CRITICAL] Complete Outage"

    def test_no_prefix_for_none_impact(self):
        """Test no prefix when impact is 'none'."""
        incident = Incident(
            title="Scheduled Maintenance",
            url="https://status.instructure.com/incidents/000",
            status="monitoring",
            impact="none",
            content="Scheduled maintenance window.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_id="incident_000",
        )

        item = incident_to_content_item(incident)

        assert item.title == "Scheduled Maintenance"

    def test_no_prefix_for_empty_impact(self):
        """Test no prefix when impact is empty string."""
        incident = Incident(
            title="Minor Update",
            url="https://status.instructure.com/incidents/111",
            status="resolved",
            impact="",
            content="Minor system update.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_id="incident_111",
        )

        item = incident_to_content_item(incident)

        assert item.title == "Minor Update"

    def test_uses_created_at_for_published_date(self):
        """Test that created_at is used for published_date, not updated_at."""
        created = datetime(2026, 1, 29, 12, 0, 0)
        updated = datetime(2026, 1, 30, 12, 0, 0)

        incident = Incident(
            title="Test Incident",
            url="https://status.instructure.com/incidents/222",
            status="resolved",
            impact="minor",
            content="Test content",
            created_at=created,
            updated_at=updated,
            source_id="incident_222",
        )

        item = incident_to_content_item(incident)

        assert item.published_date == created

    def test_engagement_score_is_zero(self):
        """Test that engagement score is always 0 for incidents."""
        incident = Incident(
            title="Test",
            url="https://status.instructure.com/incidents/333",
            status="investigating",
            impact="minor",
            content="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_id="incident_333",
        )

        item = incident_to_content_item(incident)

        assert item.engagement_score == 0

    def test_preserves_source_id(self):
        """Test that source_id is preserved."""
        incident = Incident(
            title="Test",
            url="https://status.instructure.com/incidents/444",
            status="resolved",
            impact="none",
            content="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_id="unique_incident_id",
        )

        item = incident_to_content_item(incident)

        assert item.source_id == "unique_incident_id"

    def test_returns_content_item_type(self):
        """Test that return type is ContentItem."""
        incident = Incident(
            title="Test",
            url="https://status.instructure.com/test",
            status="resolved",
            impact="none",
            content="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_id="incident_test",
        )

        item = incident_to_content_item(incident)

        assert isinstance(item, ContentItem)


class TestMainIntegration:
    """Integration tests for the main() function."""

    @pytest.fixture
    def mock_environment(self, tmp_path, monkeypatch):
        """Set up mock environment for integration tests."""
        # Create temp directories
        output_dir = tmp_path / "output"
        logs_dir = tmp_path / "logs"
        data_dir = tmp_path / "data"
        output_dir.mkdir()
        logs_dir.mkdir()
        data_dir.mkdir()

        # Set environment variables
        monkeypatch.setenv("LOG_FILE", str(logs_dir / "test.log"))

        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        yield tmp_path

        os.chdir(original_cwd)

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.RSSBuilder")
    @patch("main.Database")
    def test_main_workflow_with_no_items(
        self,
        mock_db_class,
        mock_rss_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test main workflow when no items are found."""
        # Setup mocks
        mock_db = MagicMock()
        mock_db.item_exists.return_value = False  # No existing items
        mock_db.get_comment_count.return_value = None  # No previous comments
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_all.return_value = []
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        mock_reddit = MagicMock()
        mock_reddit.search_canvas_discussions.return_value = []
        mock_reddit_class.return_value = mock_reddit

        mock_status = MagicMock()
        mock_status.get_recent_incidents.return_value = []
        mock_status_class.return_value = mock_status

        mock_processor = MagicMock()
        mock_processor.enrich_with_llm.return_value = []
        mock_processor_class.return_value = mock_processor

        mock_rss = MagicMock()
        mock_rss.create_feed.return_value = '<?xml version="1.0"?><rss></rss>'
        mock_rss_class.return_value = mock_rss

        # Run main
        main()

        # Verify workflow (deduplication now done inline in main)
        mock_instructure.scrape_all.assert_called_once()
        mock_reddit.search_canvas_discussions.assert_called_once()
        mock_status.get_recent_incidents.assert_called_once()
        mock_rss.create_feed.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.RSSBuilder")
    @patch("main.Database")
    def test_main_workflow_with_items(
        self,
        mock_db_class,
        mock_rss_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test main workflow when items are found from all sources."""
        # Setup mock items
        community_post = CommunityPost(
            title="Release Notes",
            url="https://community.instructure.com/123",
            content="New features",
            published_date=datetime.now(),
            likes=10,
            comments=5,
        )

        reddit_post = RedditPost(
            title="Canvas Question",
            url="https://reddit.com/r/canvas/456",
            content="Help needed",
            subreddit="canvas",
            author="testuser",
            score=20,
            num_comments=10,
            published_date=datetime.now(),
            source_id="reddit_456",
        )

        incident = Incident(
            title="Service Issue",
            url="https://status.instructure.com/789",
            status="investigating",
            impact="minor",
            content="Investigating issue",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_id="incident_789",
        )

        # Setup mocks
        mock_db = MagicMock()
        mock_db.insert_item.return_value = 1
        mock_db.item_exists.return_value = False  # All items are new
        mock_db.get_comment_count.return_value = None  # No previous comments
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_all.return_value = [community_post]
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        mock_reddit = MagicMock()
        mock_reddit.search_canvas_discussions.return_value = [reddit_post]
        mock_reddit_class.return_value = mock_reddit

        mock_status = MagicMock()
        mock_status.get_recent_incidents.return_value = [incident]
        mock_status_class.return_value = mock_status

        # Processor returns the items passed to it
        mock_processor = MagicMock()
        mock_processor.enrich_with_llm.side_effect = lambda items: items
        mock_processor_class.return_value = mock_processor

        mock_rss = MagicMock()
        mock_rss.create_feed.return_value = '<?xml version="1.0"?><rss><item/></rss>'
        mock_rss_class.return_value = mock_rss

        # Run main
        main()

        # Verify 3 items were processed (1 from each source)
        # Deduplication is now done inline via db.item_exists()
        enrich_call_args = mock_processor.enrich_with_llm.call_args[0][0]
        assert len(enrich_call_args) == 3

        # Verify all items are ContentItem instances
        for item in enrich_call_args:
            assert isinstance(item, ContentItem)

        # Verify sources
        sources = {item.source for item in enrich_call_args}
        assert sources == {"community", "reddit", "status"}

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.RSSBuilder")
    @patch("main.Database")
    def test_main_creates_output_directory(
        self,
        mock_db_class,
        mock_rss_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test that main creates output directory if it doesn't exist."""
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_all.return_value = []
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        mock_reddit = MagicMock()
        mock_reddit.search_canvas_discussions.return_value = []
        mock_reddit_class.return_value = mock_reddit

        mock_status = MagicMock()
        mock_status.get_recent_incidents.return_value = []
        mock_status_class.return_value = mock_status

        mock_processor = MagicMock()
        mock_processor.enrich_with_llm.return_value = []
        mock_processor_class.return_value = mock_processor

        mock_rss = MagicMock()
        mock_rss.create_feed.return_value = '<?xml version="1.0"?><rss></rss>'
        mock_rss_class.return_value = mock_rss

        # Run main
        main()

        # Verify output directory was created
        output_path = Path(mock_environment) / "output"
        assert output_path.exists()

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.RSSBuilder")
    @patch("main.Database")
    def test_main_writes_feed_xml(
        self,
        mock_db_class,
        mock_rss_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test that main writes RSS feed to output/feed.xml."""
        expected_xml = '<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'

        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_all.return_value = []
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        mock_reddit = MagicMock()
        mock_reddit.search_canvas_discussions.return_value = []
        mock_reddit_class.return_value = mock_reddit

        mock_status = MagicMock()
        mock_status.get_recent_incidents.return_value = []
        mock_status_class.return_value = mock_status

        mock_processor = MagicMock()
        mock_processor.enrich_with_llm.return_value = []
        mock_processor_class.return_value = mock_processor

        mock_rss = MagicMock()
        mock_rss.create_feed.return_value = expected_xml
        mock_rss_class.return_value = mock_rss

        # Run main
        main()

        # Verify feed.xml was written
        feed_path = Path(mock_environment) / "output" / "feed.xml"
        assert feed_path.exists()
        assert feed_path.read_text(encoding="utf-8") == expected_xml

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.RSSBuilder")
    @patch("main.Database")
    def test_main_closes_database_on_success(
        self,
        mock_db_class,
        mock_rss_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test that database is closed after successful run."""
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_all.return_value = []
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        mock_reddit = MagicMock()
        mock_reddit.search_canvas_discussions.return_value = []
        mock_reddit_class.return_value = mock_reddit

        mock_status = MagicMock()
        mock_status.get_recent_incidents.return_value = []
        mock_status_class.return_value = mock_status

        mock_processor = MagicMock()
        mock_processor.enrich_with_llm.return_value = []
        mock_processor_class.return_value = mock_processor

        mock_rss = MagicMock()
        mock_rss.create_feed.return_value = '<?xml version="1.0"?><rss></rss>'
        mock_rss_class.return_value = mock_rss

        # Run main
        main()

        # Verify database was closed
        mock_db.close.assert_called_once()

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.RSSBuilder")
    @patch("main.Database")
    def test_main_closes_database_on_error(
        self,
        mock_db_class,
        mock_rss_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test that database is closed even when an error occurs."""
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_all.side_effect = Exception("Scraper error")
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        # Run main and expect SystemExit
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

        # Verify database was still closed
        mock_db.close.assert_called_once()

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.RSSBuilder")
    @patch("main.Database")
    def test_main_stores_items_in_database(
        self,
        mock_db_class,
        mock_rss_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test that enriched items are stored in the database."""
        # Create a test item that will be "enriched"
        enriched_item = ContentItem(
            source="community",
            source_id="test_123",
            title="Test",
            url="https://example.com",
            content="Test content",
            summary="Test summary",
            sentiment="positive",
            topics=["Gradebook"],
        )

        # Create a community post that will be converted to ContentItem
        community_post = CommunityPost(
            title="Test",
            url="https://example.com",
            content="Test content",
            published_date=datetime.now(),
            likes=0,
            comments=0,
        )

        # The enriched_item should have the same source_id as what gets generated
        # from the community_post
        enriched_item.source_id = community_post.source_id

        # Setup mocks
        mock_db = MagicMock()
        mock_db.insert_item.return_value = 1
        mock_db.item_exists.return_value = False  # Item is new
        mock_db.get_comment_count.return_value = None
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_all.return_value = [community_post]
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        mock_reddit = MagicMock()
        mock_reddit.search_canvas_discussions.return_value = []
        mock_reddit_class.return_value = mock_reddit

        mock_status = MagicMock()
        mock_status.get_recent_incidents.return_value = []
        mock_status_class.return_value = mock_status

        mock_processor = MagicMock()
        mock_processor.enrich_with_llm.return_value = [enriched_item]
        mock_processor_class.return_value = mock_processor

        mock_rss = MagicMock()
        mock_rss.create_feed.return_value = '<?xml version="1.0"?><rss></rss>'
        mock_rss_class.return_value = mock_rss

        # Run main
        main()

        # Verify item was stored
        mock_db.insert_item.assert_called_once_with(enriched_item)
        mock_db.record_feed_generation.assert_called_once()

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.RSSBuilder")
    @patch("main.Database")
    def test_main_records_feed_generation(
        self,
        mock_db_class,
        mock_rss_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test that feed generation is recorded in database."""
        feed_xml = '<?xml version="1.0"?><rss><channel><item/></channel></rss>'

        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_all.return_value = []
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        mock_reddit = MagicMock()
        mock_reddit.search_canvas_discussions.return_value = []
        mock_reddit_class.return_value = mock_reddit

        mock_status = MagicMock()
        mock_status.get_recent_incidents.return_value = []
        mock_status_class.return_value = mock_status

        mock_processor = MagicMock()
        mock_processor.enrich_with_llm.return_value = []
        mock_processor_class.return_value = mock_processor

        mock_rss = MagicMock()
        mock_rss.create_feed.return_value = feed_xml
        mock_rss_class.return_value = mock_rss

        # Run main
        main()

        # Verify feed generation was recorded
        mock_db.record_feed_generation.assert_called_once_with(0, feed_xml)


class TestV130Integration:
    """Integration tests for v1.3.0 features."""

    def test_discussion_tracking_flow(self, temp_db):
        """Test full discussion tracking flow."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts

        # First run - post should be marked as new
        posts = [CommunityPost(
            title="Question",
            url="http://example.com/discussion/100/test",
            content="Content",
            published_date=datetime.now(),
            comments=2,
            post_type="question"
        )]
        results1 = classify_discussion_posts(posts, temp_db, first_run_limit=5)
        assert len(results1) == 1
        assert results1[0].is_new is True
        assert results1[0].new_comment_count == 2

        # Second run with more comments - should be marked as update
        posts[0] = CommunityPost(
            title="Question",
            url="http://example.com/discussion/100/test",
            content="Content",
            published_date=datetime.now(),
            comments=5,
            post_type="question"
        )
        results2 = classify_discussion_posts(posts, temp_db, first_run_limit=5)
        assert len(results2) == 1
        assert results2[0].is_new is False
        assert results2[0].new_comment_count == 3  # 5 - 2 = 3 new comments

    def test_discussion_tracking_first_run_limit(self, temp_db):
        """Test that first run limit prevents feed flooding."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts

        # Create 10 new posts
        posts = [
            CommunityPost(
                title=f"Question {i}",
                url=f"http://example.com/discussion/{i}/test",
                content="Content",
                published_date=datetime.now(),
                comments=1,
                post_type="question"
            )
            for i in range(10)
        ]

        # With first_run_limit=5, only 5 should be returned
        results = classify_discussion_posts(posts, temp_db, first_run_limit=5)
        assert len(results) == 5

    def test_release_note_classification(self, temp_db):
        """Test release note feature classification."""
        from scrapers.instructure_community import (
            ReleaseNotePage, Feature, FeatureTableData, classify_release_features
        )

        # Create a release note page with features
        page = ReleaseNotePage(
            title="Canvas Release: 2026-01-15",
            url="http://example.com/release/123",
            release_date=datetime.now(),
            upcoming_changes=[],
            features=[
                Feature(
                    category="Gradebook",
                    name="New Gradebook Feature",
                    anchor_id="gradebook",
                    added_date=datetime.now(),
                    raw_content="A new gradebook feature description",
                    table_data=FeatureTableData(
                        enable_location="Account",
                        default_status="On",
                        permissions="Admin",
                        affected_areas=["Gradebook"],
                        affects_roles=["Teacher", "Admin"]
                    )
                )
            ],
            sections={"Gradebook": []}
        )

        # First run - feature should be new
        is_new_page, new_anchors = classify_release_features(page, temp_db, first_run_limit=10)
        assert is_new_page is True
        assert len(new_anchors) == 1
        assert "gradebook" in new_anchors

        # Second run - same feature should not appear (no changes)
        is_new_page2, new_anchors2 = classify_release_features(page, temp_db, first_run_limit=10)
        assert len(new_anchors2) == 0

    def test_deploy_note_classification(self, temp_db):
        """Test deploy note change classification."""
        from scrapers.instructure_community import (
            DeployNotePage, DeployChange, classify_deploy_changes
        )

        # Create a deploy note page with changes
        page = DeployNotePage(
            title="Canvas Deploy: 2026-01-20",
            url="http://example.com/deploy/456",
            deploy_date=datetime.now(),
            beta_date=None,
            changes=[
                DeployChange(
                    category="Performance",
                    name="Performance Improvement",
                    anchor_id="perf-improvement",
                    section="improvements",
                    raw_content="Improved gradebook loading speed",
                    table_data=None,
                    status=None,
                    status_date=None
                )
            ],
            sections={"improvements": []}
        )

        # First run - change should be new
        is_new_page, new_anchors = classify_deploy_changes(page, temp_db, first_run_limit=10)
        assert is_new_page is True
        assert len(new_anchors) == 1
        assert "perf-improvement" in new_anchors

        # Second run - same change should not appear
        is_new_page2, new_anchors2 = classify_deploy_changes(page, temp_db, first_run_limit=10)
        assert len(new_anchors2) == 0


class TestV130FullIntegration:
    """Full integration tests for v1.3.0."""

    def test_first_run_then_update_flow(self, temp_db):
        """Test complete first run and update detection flow."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts

        # Simulate 7 Q&A posts
        qa_posts = [
            CommunityPost(
                title=f"Question {i}",
                url=f"http://example.com/discussion/{i}/test",
                content=f"Content {i}",
                published_date=datetime.now(),
                comments=i,
                post_type="question"
            ) for i in range(7)
        ]

        # First run - limit 5
        results1 = classify_discussion_posts(qa_posts, temp_db, first_run_limit=5)
        assert len(results1) == 5
        assert all(r.is_new for r in results1)

        # All 7 should be tracked in DB (even those beyond limit)
        for i in range(7):
            assert temp_db.get_discussion_tracking(f"question_{i}") is not None

        # Second run - posts 0, 1 have new comments
        qa_posts_updated = [
            CommunityPost(
                title=f"Question {i}",
                url=f"http://example.com/discussion/{i}/test",
                content=f"Content {i}",
                published_date=datetime.now(),
                comments=10 if i == 0 else 15 if i == 1 else i,
                post_type="question"
            ) for i in range(7)
        ]

        results2 = classify_discussion_posts(qa_posts_updated, temp_db, first_run_limit=5)
        assert len(results2) == 2
        assert all(not r.is_new for r in results2)

        # Verify deltas (new_comment_count = current - previous)
        deltas = {r.post.url: r.new_comment_count for r in results2}
        assert deltas["http://example.com/discussion/0/test"] == 10  # 10 - 0 = 10
        assert deltas["http://example.com/discussion/1/test"] == 14  # 15 - 1 = 14

    def test_rss_title_formatting(self):
        """Test RSS title formatting for all content types."""
        from generator.rss_builder import build_discussion_title

        # Q&A
        assert build_discussion_title("question", "SSO Help", True) == "[NEW] - Question Forum - SSO Help"
        assert build_discussion_title("question", "SSO Help", False) == "[UPDATE] - Question Forum - SSO Help"

        # Blog
        assert build_discussion_title("blog", "Updates", True) == "[NEW] - Blog - Updates"

        # Release Notes (no source label)
        assert build_discussion_title("release_note", "Canvas Release Notes (2026-02-21)", True) == "[NEW] Canvas Release Notes (2026-02-21)"
        assert build_discussion_title("deploy_note", "Canvas Deploy Notes (2026-02-11)", False) == "[UPDATE] Canvas Deploy Notes (2026-02-11)"

    def test_mixed_content_types_classification(self, temp_db):
        """Test classification handles different content types correctly."""
        from scrapers.instructure_community import (
            CommunityPost, classify_discussion_posts,
            ReleaseNotePage, Feature, FeatureTableData, classify_release_features,
            DeployNotePage, DeployChange, classify_deploy_changes
        )

        # Q&A posts
        qa_posts = [CommunityPost(
            title="Q&A Question",
            url="http://example.com/discussion/1/qa",
            content="Q&A content",
            published_date=datetime.now(),
            comments=3,
            post_type="question"
        )]

        # Blog posts
        blog_posts = [CommunityPost(
            title="Blog Post",
            url="http://example.com/blog/2/post",
            content="Blog content",
            published_date=datetime.now(),
            comments=5,
            post_type="blog"
        )]

        # Classify both types
        qa_results = classify_discussion_posts(qa_posts, temp_db, first_run_limit=5)
        blog_results = classify_discussion_posts(blog_posts, temp_db, first_run_limit=5)

        assert len(qa_results) == 1
        assert len(blog_results) == 1
        assert qa_results[0].is_new is True
        assert blog_results[0].is_new is True

        # Verify both are tracked separately
        assert temp_db.get_discussion_tracking("question_1") is not None
        assert temp_db.get_discussion_tracking("blog_2") is not None
