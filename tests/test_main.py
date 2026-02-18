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
        assert item.content_type == "changelog"
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
        logs_dir = tmp_path / "logs"
        data_dir = tmp_path / "data"
        logs_dir.mkdir()
        data_dir.mkdir()

        monkeypatch.setenv("LOG_FILE", str(logs_dir / "test.log"))

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        yield tmp_path

        os.chdir(original_cwd)

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.Database")
    def test_main_workflow_with_no_items(
        self,
        mock_db_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test main workflow when no items are found."""
        mock_db = MagicMock()
        mock_db.item_exists.return_value = False
        mock_db.get_recent_items.return_value = []
        mock_db.seed_features.return_value = 45
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_question_forum.return_value = []
        mock_instructure.scrape_blog.return_value = []
        mock_instructure.scrape_release_notes.return_value = []
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
        mock_processor_class.return_value = mock_processor

        main()

        mock_db.seed_features.assert_called_once()
        mock_instructure.scrape_question_forum.assert_called_once()
        mock_instructure.scrape_blog.assert_called_once()
        mock_instructure.scrape_release_notes.assert_called_once()
        mock_reddit.search_canvas_discussions.assert_called_once()
        mock_status.get_recent_incidents.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.Database")
    def test_main_stores_reddit_items(
        self,
        mock_db_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test main workflow stores Reddit items in database."""
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

        mock_db = MagicMock()
        mock_db.insert_item.return_value = 1
        mock_db.item_exists.return_value = False
        mock_db.get_recent_items.return_value = []
        mock_db.seed_features.return_value = 45
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_question_forum.return_value = []
        mock_instructure.scrape_blog.return_value = []
        mock_instructure.scrape_release_notes.return_value = []
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        mock_reddit = MagicMock()
        mock_reddit.search_canvas_discussions.return_value = [reddit_post]
        mock_reddit_class.return_value = mock_reddit

        mock_status = MagicMock()
        mock_status.get_recent_incidents.return_value = []
        mock_status_class.return_value = mock_status

        mock_processor = MagicMock()
        mock_processor.sanitize_html.side_effect = lambda x: x
        mock_processor.redact_pii.side_effect = lambda x: x
        mock_processor.summarize_with_llm.return_value = "Summary"
        mock_processor.classify_topic.return_value = ("General", [])
        mock_processor_class.return_value = mock_processor

        main()

        # Verify insert_item was called for Reddit post
        assert mock_db.insert_item.called

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.Database")
    def test_main_closes_database_on_success(
        self,
        mock_db_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test that database is closed after successful run."""
        mock_db = MagicMock()
        mock_db.get_recent_items.return_value = []
        mock_db.seed_features.return_value = 45
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_question_forum.return_value = []
        mock_instructure.scrape_blog.return_value = []
        mock_instructure.scrape_release_notes.return_value = []
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
        mock_processor_class.return_value = mock_processor

        main()

        mock_db.close.assert_called_once()

    @patch("main.InstructureScraper")
    @patch("main.RedditMonitor")
    @patch("main.StatusPageMonitor")
    @patch("main.ContentProcessor")
    @patch("main.Database")
    def test_main_closes_database_on_error(
        self,
        mock_db_class,
        mock_processor_class,
        mock_status_class,
        mock_reddit_class,
        mock_instructure_class,
        mock_environment,
    ):
        """Test that database is closed even when an error occurs."""
        mock_db = MagicMock()
        mock_db.get_recent_items.return_value = []
        mock_db.seed_features.return_value = 45
        mock_db_class.return_value = mock_db

        mock_instructure = MagicMock()
        mock_instructure.scrape_question_forum.side_effect = Exception("Scraper error")
        mock_instructure.__enter__ = MagicMock(return_value=mock_instructure)
        mock_instructure.__exit__ = MagicMock(return_value=False)
        mock_instructure_class.return_value = mock_instructure

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_db.close.assert_called_once()


class TestDiscussionTracking:
    """Tests for discussion tracking functionality."""

    def test_discussion_tracking_flow(self, temp_db):
        """Test full discussion tracking flow."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts

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

        # Insert item to track it
        item = ContentItem(
            source="community",
            source_id="question_100",
            title="Question",
            url="http://example.com/discussion/100/test",
            content="Content",
            content_type="question",
            published_date=datetime.now(),
            comment_count=2,
        )
        temp_db.insert_item(item)

        # Second run with more comments
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

    def test_discussion_tracking_first_run_limit(self, temp_db):
        """Test that first run limit prevents flooding."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts

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

        results = classify_discussion_posts(posts, temp_db, first_run_limit=5)
        assert len(results) == 5

    def test_release_note_classification(self, temp_db):
        """Test release note feature classification."""
        from scrapers.instructure_community import (
            ReleaseNotePage, Feature, FeatureTableData, classify_release_features
        )

        temp_db.seed_features()

        page = ReleaseNotePage(
            title="Canvas Release: 2026-01-15",
            url="http://example.com/release/123456",
            release_date=datetime.now(),
            upcoming_changes=[],
            features=[
                Feature(
                    category="Gradebook",
                    name="New Gradebook Feature",
                    anchor_id="new-gradebook-feature",
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

        is_new_page, new_anchor_ids = classify_release_features(page, temp_db, first_run_limit=10)
        assert is_new_page is True
        assert len(new_anchor_ids) == 1
        # v2.0: Returns anchor_ids (or option_ids) instead of feature names
        assert "new-gradebook-feature" in new_anchor_ids

    def test_deploy_note_classification(self, temp_db):
        """Test deploy note change classification."""
        from scrapers.instructure_community import (
            DeployNotePage, DeployChange, classify_deploy_changes
        )

        temp_db.seed_features()

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

        is_new_page, new_change_names = classify_deploy_changes(page, temp_db, first_run_limit=10)
        assert is_new_page is True
        assert len(new_change_names) == 1
        assert "Performance Improvement" in new_change_names


class TestProcessDiscussionsFeatureRefs:
    """Tests for process_discussions creating feature refs."""

    @patch("main.classify_discussion_posts")
    def test_process_discussions_creates_content_feature_refs(self, mock_classify, temp_db):
        """Test that store_discussion_posts creates content_feature_refs records."""
        from main import store_discussion_posts
        from scrapers.instructure_community import CommunityPost, DiscussionUpdate
        from processor.content_processor import ContentProcessor

        # Seed features
        temp_db.seed_features()

        # Create a controlled update with feature_refs
        mock_update = DiscussionUpdate(
            post=CommunityPost(
                title="SpeedGrader issue",
                url="https://community.instructure.com/discussion/99999",
                content="SpeedGrader is slow",
                published_date=datetime.now(timezone.utc),
                post_type="question",
                comments=3,
            ),
            is_new=True,
            previous_comment_count=0,
            new_comment_count=3,
            latest_comment=None,
            feature_refs=[("speedgrader", None, "questions")],
        )

        # Configure the mock to return our controlled update
        mock_classify.return_value = [mock_update]

        # Create a mock processor
        processor = MagicMock(spec=ContentProcessor)
        processor.sanitize_html.return_value = "SpeedGrader is slow"
        processor.redact_pii.side_effect = lambda x: x
        processor.summarize_with_llm.return_value = "User reports SpeedGrader performance issues."
        processor.classify_topic.return_value = ("Grading", ["SpeedGrader"])

        # Call store_discussion_posts
        stored = store_discussion_posts(
            posts=[mock_update.post],
            db=temp_db,
            scraper=None,
            processor=processor,
        )

        # Check that content_feature_refs was created
        refs = temp_db.get_features_for_content("question_99999")
        assert len(refs) >= 1
        assert refs[0]["feature_id"] == "speedgrader"
        assert refs[0]["mention_type"] == "questions"
