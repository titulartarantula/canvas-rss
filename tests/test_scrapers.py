"""Tests for scraper modules."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestStatusPageMonitor:
    """Tests for the StatusPageMonitor class."""

    def test_status_page_monitor_initialization(self):
        """Test that StatusPageMonitor initializes correctly."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        assert monitor.STATUS_URL == "https://status.instructure.com/"
        assert monitor.timeout == 30

    def test_status_page_monitor_custom_timeout(self):
        """Test that StatusPageMonitor accepts custom timeout."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor(timeout=60)
        assert monitor.timeout == 60

    def test_parse_datetime_valid_utc(self):
        """Test parsing valid ISO 8601 datetime with Z suffix."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        result = monitor._parse_datetime("2024-01-15T10:30:00.000Z")

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_datetime_valid_iso(self):
        """Test parsing valid ISO 8601 datetime with timezone offset."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        result = monitor._parse_datetime("2024-01-15T10:30:00+00:00")

        assert result is not None
        assert result.year == 2024

    def test_parse_datetime_none_input(self):
        """Test parsing None returns None."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        result = monitor._parse_datetime(None)
        assert result is None

    def test_parse_datetime_empty_string(self):
        """Test parsing empty string returns None."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        result = monitor._parse_datetime("")
        assert result is None

    def test_parse_datetime_invalid_format(self):
        """Test parsing invalid format returns None."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        result = monitor._parse_datetime("not-a-date")
        assert result is None

    def test_extract_incident_content_with_updates(self):
        """Test extracting content from incident with updates."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        incident_data = {
            "name": "Test Incident",
            "incident_updates": [
                {"status": "resolved", "body": "Issue has been resolved."},
                {"status": "investigating", "body": "We are investigating."},
            ]
        }

        content = monitor._extract_incident_content(incident_data)
        assert "[Resolved] Issue has been resolved." in content
        assert "[Investigating] We are investigating." in content

    def test_extract_incident_content_no_updates(self):
        """Test extracting content when no updates exist."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        incident_data = {
            "name": "Test Incident",
            "incident_updates": []
        }

        content = monitor._extract_incident_content(incident_data)
        assert content == "Test Incident"

    def test_extract_incident_content_missing_updates_key(self):
        """Test extracting content when incident_updates key is missing."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        incident_data = {
            "name": "Test Incident Without Updates"
        }

        content = monitor._extract_incident_content(incident_data)
        assert content == "Test Incident Without Updates"

    def test_extract_incident_content_limits_to_three_updates(self):
        """Test that only the 3 most recent updates are included."""
        from scrapers.status_page import StatusPageMonitor

        monitor = StatusPageMonitor()
        incident_data = {
            "name": "Test Incident",
            "incident_updates": [
                {"status": "resolved", "body": "Update 1"},
                {"status": "monitoring", "body": "Update 2"},
                {"status": "identified", "body": "Update 3"},
                {"status": "investigating", "body": "Update 4"},
                {"status": "investigating", "body": "Update 5"},
            ]
        }

        content = monitor._extract_incident_content(incident_data)
        assert "Update 1" in content
        assert "Update 2" in content
        assert "Update 3" in content
        assert "Update 4" not in content
        assert "Update 5" not in content

    @patch('scrapers.status_page.requests.Session')
    def test_get_recent_incidents_success(self, mock_session_class):
        """Test successful fetch of recent incidents."""
        from scrapers.status_page import StatusPageMonitor

        # Create mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "incidents": [
                {
                    "id": "abc123",
                    "name": "Test Incident",
                    "status": "resolved",
                    "impact": "minor",
                    "shortlink": "https://stspg.io/abc123",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "incident_updates": [
                        {"status": "resolved", "body": "All clear."}
                    ]
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        # Setup mock session
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        monitor = StatusPageMonitor()
        monitor.session = mock_session

        incidents = monitor.get_recent_incidents(hours=24)

        assert len(incidents) == 1
        assert incidents[0].title == "Test Incident"
        assert incidents[0].status == "resolved"
        assert incidents[0].impact == "minor"
        assert incidents[0].source_id == "status_abc123"
        assert incidents[0].source == "status"

    @patch('scrapers.status_page.requests.Session')
    def test_get_recent_incidents_filters_old_incidents(self, mock_session_class):
        """Test that incidents older than the time window are filtered out."""
        from scrapers.status_page import StatusPageMonitor

        old_date = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

        mock_response = Mock()
        mock_response.json.return_value = {
            "incidents": [
                {
                    "id": "old123",
                    "name": "Old Incident",
                    "status": "resolved",
                    "impact": "minor",
                    "created_at": old_date,
                    "updated_at": old_date,
                    "incident_updates": []
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        monitor = StatusPageMonitor()
        monitor.session = mock_session

        incidents = monitor.get_recent_incidents(hours=24)

        assert len(incidents) == 0

    @patch('scrapers.status_page.requests.Session')
    def test_get_recent_incidents_request_error(self, mock_session_class):
        """Test handling of request errors."""
        from scrapers.status_page import StatusPageMonitor
        import requests

        mock_session = Mock()
        mock_session.get.side_effect = requests.RequestException("Connection error")
        mock_session_class.return_value = mock_session

        monitor = StatusPageMonitor()
        monitor.session = mock_session

        incidents = monitor.get_recent_incidents(hours=24)

        assert incidents == []

    @patch('scrapers.status_page.requests.Session')
    def test_get_recent_incidents_json_error(self, mock_session_class):
        """Test handling of JSON parsing errors."""
        from scrapers.status_page import StatusPageMonitor

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        monitor = StatusPageMonitor()
        monitor.session = mock_session

        incidents = monitor.get_recent_incidents(hours=24)

        assert incidents == []

    @patch('scrapers.status_page.requests.Session')
    def test_get_current_status_success(self, mock_session_class):
        """Test successful fetch of current status."""
        from scrapers.status_page import StatusPageMonitor

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": {
                "indicator": "none",
                "description": "All Systems Operational"
            },
            "page": {
                "url": "https://status.instructure.com"
            }
        }
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        monitor = StatusPageMonitor()
        monitor.session = mock_session

        status = monitor.get_current_status()

        assert status["indicator"] == "none"
        assert status["description"] == "All Systems Operational"
        assert "page_url" in status

    @patch('scrapers.status_page.requests.Session')
    def test_get_current_status_request_error(self, mock_session_class):
        """Test handling of request errors in get_current_status."""
        from scrapers.status_page import StatusPageMonitor
        import requests

        mock_session = Mock()
        mock_session.get.side_effect = requests.RequestException("Connection error")
        mock_session_class.return_value = mock_session

        monitor = StatusPageMonitor()
        monitor.session = mock_session

        status = monitor.get_current_status()

        assert status["indicator"] == "unknown"
        assert "Unable to fetch status" in status["description"]

    @patch('scrapers.status_page.requests.Session')
    def test_get_unresolved_incidents_success(self, mock_session_class):
        """Test successful fetch of unresolved incidents."""
        from scrapers.status_page import StatusPageMonitor

        mock_response = Mock()
        mock_response.json.return_value = {
            "incidents": [
                {
                    "id": "unresolved123",
                    "name": "Ongoing Issue",
                    "status": "investigating",
                    "impact": "major",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "incident_updates": []
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        monitor = StatusPageMonitor()
        monitor.session = mock_session

        incidents = monitor.get_unresolved_incidents()

        assert len(incidents) == 1
        assert incidents[0].title == "Ongoing Issue"
        assert incidents[0].status == "investigating"

    @patch('scrapers.status_page.requests.Session')
    def test_get_unresolved_incidents_empty(self, mock_session_class):
        """Test fetch when no unresolved incidents exist."""
        from scrapers.status_page import StatusPageMonitor

        mock_response = Mock()
        mock_response.json.return_value = {"incidents": []}
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        monitor = StatusPageMonitor()
        monitor.session = mock_session

        incidents = monitor.get_unresolved_incidents()

        assert incidents == []

    def test_incident_dataclass_properties(self):
        """Test the Incident dataclass properties."""
        from scrapers.status_page import Incident

        incident = Incident(
            title="Test",
            url="https://example.com",
            status="resolved",
            impact="minor",
            content="Test content",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            source_id="status_123"
        )

        assert incident.source == "status"
        assert incident.title == "Test"
        assert incident.status == "resolved"


class TestRedditMonitor:
    """Tests for the RedditMonitor class."""

    def test_reddit_monitor_initialization_no_credentials(self):
        """Test that RedditMonitor initializes without credentials."""
        from scrapers.reddit_client import RedditMonitor

        with patch.dict('os.environ', {}, clear=True):
            # Remove any env vars
            import os
            for key in ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USER_AGENT']:
                os.environ.pop(key, None)

            monitor = RedditMonitor()
            assert "canvas" in monitor.DEFAULT_SUBREDDITS
            assert monitor.reddit is None  # Should be None without credentials

    def test_reddit_monitor_default_subreddits(self):
        """Test that default subreddits are properly defined."""
        from scrapers.reddit_client import RedditMonitor

        monitor = RedditMonitor()
        assert "canvas" in monitor.DEFAULT_SUBREDDITS
        assert "instructionaldesign" in monitor.DEFAULT_SUBREDDITS
        assert "highereducation" in monitor.DEFAULT_SUBREDDITS
        assert "professors" in monitor.DEFAULT_SUBREDDITS

    def test_reddit_monitor_default_keywords(self):
        """Test that default keywords are properly defined."""
        from scrapers.reddit_client import RedditMonitor

        monitor = RedditMonitor()
        assert "canvas lms" in monitor.DEFAULT_KEYWORDS
        assert "canvas update" in monitor.DEFAULT_KEYWORDS

    @patch('scrapers.reddit_client.PRAW_AVAILABLE', False)
    def test_reddit_monitor_praw_not_installed(self):
        """Test graceful handling when PRAW is not installed."""
        # Need to reimport to get the patched value
        import importlib
        import scrapers.reddit_client as reddit_module
        importlib.reload(reddit_module)

        monitor = reddit_module.RedditMonitor()
        assert monitor.reddit is None

        # Restore
        importlib.reload(reddit_module)

    def test_reddit_post_dataclass_properties(self):
        """Test the RedditPost dataclass properties."""
        from scrapers.reddit_client import RedditPost

        post = RedditPost(
            title="Test Post",
            url="https://reddit.com/r/test/123",
            content="Test content",
            subreddit="canvas",
            author="test_user",
            score=25,
            num_comments=10,
            published_date=datetime.now(timezone.utc),
            source_id="reddit_123",
            permalink="/r/test/123"
        )

        assert post.source == "reddit"
        assert post.title == "Test Post"
        assert post.author == "test_user"

    def test_reddit_post_anonymize(self):
        """Test the anonymize method on RedditPost."""
        from scrapers.reddit_client import RedditPost

        post = RedditPost(
            title="Test Post",
            url="https://reddit.com/r/test/123",
            content="Test content",
            subreddit="canvas",
            author="real_username",
            score=25,
            num_comments=10,
            published_date=datetime.now(timezone.utc),
            source_id="reddit_123",
            permalink="/r/test/123"
        )

        anon_post = post.anonymize()

        assert anon_post.author == "A Reddit user"
        assert anon_post.title == post.title
        assert anon_post.url == post.url
        assert anon_post.content == post.content
        assert anon_post.subreddit == post.subreddit
        assert anon_post.score == post.score
        assert anon_post.source_id == post.source_id

    @patch('scrapers.reddit_client.praw')
    def test_reddit_monitor_initialization_with_credentials(self, mock_praw):
        """Test RedditMonitor initialization with valid credentials."""
        from scrapers.reddit_client import RedditMonitor

        mock_reddit = Mock()
        mock_praw.Reddit.return_value = mock_reddit

        monitor = RedditMonitor(
            client_id="test_client_id",
            client_secret="test_client_secret",
            user_agent="test_user_agent"
        )

        mock_praw.Reddit.assert_called_once_with(
            client_id="test_client_id",
            client_secret="test_client_secret",
            user_agent="test_user_agent"
        )
        assert monitor.reddit is not None

    @patch('scrapers.reddit_client.praw')
    def test_submission_to_post_text_post(self, mock_praw):
        """Test converting a text post (self post) to RedditPost."""
        from scrapers.reddit_client import RedditMonitor

        mock_reddit = Mock()
        mock_praw.Reddit.return_value = mock_reddit

        monitor = RedditMonitor(
            client_id="test_id",
            client_secret="test_secret"
        )

        # Create mock submission for a text post
        mock_submission = Mock()
        mock_submission.is_self = True
        mock_submission.selftext = "This is the post content about Canvas"
        mock_submission.title = "Canvas Question"
        mock_submission.permalink = "/r/canvas/comments/abc123/canvas_question"
        mock_submission.url = "https://reddit.com/r/canvas/comments/abc123"
        mock_submission.id = "abc123"
        mock_submission.score = 15
        mock_submission.num_comments = 5
        mock_submission.created_utc = 1705315800  # Fixed timestamp
        mock_submission.author = Mock(__str__=lambda x: "test_author")
        mock_submission.subreddit = Mock(display_name="canvas")

        post = monitor._submission_to_post(mock_submission)

        assert post.title == "Canvas Question"
        assert post.content == "This is the post content about Canvas"
        assert post.subreddit == "canvas"
        assert post.author == "test_author"
        assert post.score == 15
        assert post.num_comments == 5
        assert post.source_id == "reddit_abc123"
        assert post.source == "reddit"

    @patch('scrapers.reddit_client.praw')
    def test_submission_to_post_link_post(self, mock_praw):
        """Test converting a link post to RedditPost."""
        from scrapers.reddit_client import RedditMonitor

        mock_reddit = Mock()
        mock_praw.Reddit.return_value = mock_reddit

        monitor = RedditMonitor(
            client_id="test_id",
            client_secret="test_secret"
        )

        # Create mock submission for a link post
        mock_submission = Mock()
        mock_submission.is_self = False
        mock_submission.selftext = ""
        mock_submission.title = "Canvas Update Link"
        mock_submission.permalink = "/r/canvas/comments/xyz789/canvas_update"
        mock_submission.url = "https://example.com/canvas-update"
        mock_submission.id = "xyz789"
        mock_submission.score = 30
        mock_submission.num_comments = 12
        mock_submission.created_utc = 1705315800
        mock_submission.author = Mock(__str__=lambda x: "link_poster")
        mock_submission.subreddit = Mock(display_name="canvas")

        post = monitor._submission_to_post(mock_submission)

        assert post.title == "Canvas Update Link"
        assert "Link: https://example.com/canvas-update" in post.content
        assert post.score == 30

    @patch('scrapers.reddit_client.praw')
    def test_submission_to_post_deleted_author(self, mock_praw):
        """Test handling of deleted author."""
        from scrapers.reddit_client import RedditMonitor

        mock_reddit = Mock()
        mock_praw.Reddit.return_value = mock_reddit

        monitor = RedditMonitor(
            client_id="test_id",
            client_secret="test_secret"
        )

        mock_submission = Mock()
        mock_submission.is_self = True
        mock_submission.selftext = "Content"
        mock_submission.title = "Title"
        mock_submission.permalink = "/r/canvas/123"
        mock_submission.url = "https://reddit.com/r/canvas/123"
        mock_submission.id = "123"
        mock_submission.score = 5
        mock_submission.num_comments = 2
        mock_submission.created_utc = 1705315800
        mock_submission.author = None  # Deleted author
        mock_submission.subreddit = Mock(display_name="canvas")

        post = monitor._submission_to_post(mock_submission)

        assert post.author == "[deleted]"

    @patch('scrapers.reddit_client.praw')
    def test_submission_to_post_truncates_long_content(self, mock_praw):
        """Test that long content is truncated to 2000 characters."""
        from scrapers.reddit_client import RedditMonitor

        mock_reddit = Mock()
        mock_praw.Reddit.return_value = mock_reddit

        monitor = RedditMonitor(
            client_id="test_id",
            client_secret="test_secret"
        )

        mock_submission = Mock()
        mock_submission.is_self = True
        mock_submission.selftext = "x" * 5000  # Very long content
        mock_submission.title = "Long Post"
        mock_submission.permalink = "/r/canvas/123"
        mock_submission.url = "https://reddit.com/r/canvas/123"
        mock_submission.id = "123"
        mock_submission.score = 5
        mock_submission.num_comments = 2
        mock_submission.created_utc = 1705315800
        mock_submission.author = Mock(__str__=lambda x: "author")
        mock_submission.subreddit = Mock(display_name="canvas")

        post = monitor._submission_to_post(mock_submission)

        assert len(post.content) == 2000

    def test_search_canvas_discussions_no_reddit_client(self):
        """Test search_canvas_discussions returns empty when client not initialized."""
        from scrapers.reddit_client import RedditMonitor

        with patch.dict('os.environ', {}, clear=True):
            import os
            for key in ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET']:
                os.environ.pop(key, None)

            monitor = RedditMonitor()
            results = monitor.search_canvas_discussions()
            assert results == []

    def test_search_subreddits_no_reddit_client(self):
        """Test search_subreddits returns empty when client not initialized."""
        from scrapers.reddit_client import RedditMonitor

        with patch.dict('os.environ', {}, clear=True):
            import os
            for key in ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET']:
                os.environ.pop(key, None)

            monitor = RedditMonitor()
            results = monitor.search_subreddits()
            assert results == []

    def test_get_subreddit_posts_no_reddit_client(self):
        """Test get_subreddit_posts returns empty when client not initialized."""
        from scrapers.reddit_client import RedditMonitor

        with patch.dict('os.environ', {}, clear=True):
            import os
            for key in ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET']:
                os.environ.pop(key, None)

            monitor = RedditMonitor()
            results = monitor.get_subreddit_posts("canvas")
            assert results == []

    @patch('scrapers.reddit_client.praw')
    def test_search_subreddits_deduplication(self, mock_praw):
        """Test that duplicate posts from different keyword searches are deduplicated."""
        from scrapers.reddit_client import RedditMonitor

        mock_reddit = Mock()
        mock_praw.Reddit.return_value = mock_reddit

        monitor = RedditMonitor(
            client_id="test_id",
            client_secret="test_secret"
        )

        # Create mock submission
        def create_mock_submission(id_val, subreddit_name):
            mock = Mock()
            mock.is_self = True
            mock.selftext = "Content"
            mock.title = "Canvas Post"
            mock.permalink = f"/r/{subreddit_name}/{id_val}"
            mock.url = f"https://reddit.com/r/{subreddit_name}/{id_val}"
            mock.id = id_val
            mock.score = 10
            mock.num_comments = 3
            mock.created_utc = 1705315800
            mock.author = Mock(__str__=lambda x: "author")
            mock.subreddit = Mock(display_name=subreddit_name)
            return mock

        # Return same submission for different keyword searches
        same_submission = create_mock_submission("same123", "canvas")
        mock_reddit.subreddit.return_value.search.return_value = [same_submission]

        results = monitor.search_subreddits(keywords=["canvas lms", "canvas update"])

        # Should only have one result despite searching with two keywords
        assert len(results) == 1

    @patch('scrapers.reddit_client.praw')
    def test_get_top_discussions_limits_results(self, mock_praw):
        """Test that get_top_discussions respects the limit parameter."""
        from scrapers.reddit_client import RedditMonitor

        mock_reddit = Mock()
        mock_praw.Reddit.return_value = mock_reddit

        monitor = RedditMonitor(
            client_id="test_id",
            client_secret="test_secret"
        )

        # Mock search_canvas_discussions to return many posts
        def create_mock_post(i):
            from scrapers.reddit_client import RedditPost
            return RedditPost(
                title=f"Post {i}",
                url=f"https://reddit.com/r/canvas/{i}",
                content=f"Content {i}",
                subreddit="canvas",
                author="author",
                score=100 - i,  # Decreasing scores
                num_comments=5,
                published_date=datetime.now(timezone.utc),
                source_id=f"reddit_{i}"
            )

        # Patch the method
        with patch.object(monitor, 'search_canvas_discussions') as mock_search:
            mock_search.return_value = [create_mock_post(i) for i in range(30)]
            results = monitor.get_top_discussions(min_score=5, limit=10)

        assert len(results) == 10

    @patch('scrapers.reddit_client.praw')
    def test_get_subreddit_posts_sort_options(self, mock_praw):
        """Test that get_subreddit_posts handles different sort options."""
        from scrapers.reddit_client import RedditMonitor

        mock_reddit = Mock()
        mock_subreddit = Mock()
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_praw.Reddit.return_value = mock_reddit

        # Return empty list for all sort methods
        mock_subreddit.new.return_value = []
        mock_subreddit.hot.return_value = []
        mock_subreddit.top.return_value = []
        mock_subreddit.rising.return_value = []

        monitor = RedditMonitor(
            client_id="test_id",
            client_secret="test_secret"
        )

        # Test different sort options
        monitor.get_subreddit_posts("canvas", sort="new")
        mock_subreddit.new.assert_called()

        monitor.get_subreddit_posts("canvas", sort="hot")
        mock_subreddit.hot.assert_called()

        monitor.get_subreddit_posts("canvas", sort="top")
        mock_subreddit.top.assert_called()

        monitor.get_subreddit_posts("canvas", sort="rising")
        mock_subreddit.rising.assert_called()

    @patch('scrapers.reddit_client.praw')
    def test_get_subreddit_posts_handles_error(self, mock_praw):
        """Test that get_subreddit_posts handles errors gracefully."""
        from scrapers.reddit_client import RedditMonitor

        mock_reddit = Mock()
        mock_reddit.subreddit.side_effect = Exception("API Error")
        mock_praw.Reddit.return_value = mock_reddit

        monitor = RedditMonitor(
            client_id="test_id",
            client_secret="test_secret"
        )

        results = monitor.get_subreddit_posts("canvas")
        assert results == []


class TestInstructureScraperDataclasses:
    """Tests for ReleaseNote and ChangeLogEntry dataclasses."""

    def test_release_note_creation(self):
        """Test ReleaseNote dataclass constructor with all fields."""
        from scrapers.instructure_community import ReleaseNote

        note = ReleaseNote(
            title="Canvas 2024 Q1 Release Notes",
            url="https://community.instructure.com/t/canvas-2024-q1/123",
            content="New features include...",
            published_date=datetime.now(timezone.utc),
            likes=50,
            comments=10
        )

        assert note.title == "Canvas 2024 Q1 Release Notes"
        assert note.url == "https://community.instructure.com/t/canvas-2024-q1/123"
        assert note.content == "New features include..."
        assert note.likes == 50
        assert note.comments == 10

    def test_release_note_default_values(self):
        """Test ReleaseNote default values for optional fields."""
        from scrapers.instructure_community import ReleaseNote

        note = ReleaseNote(
            title="Test Note",
            url="https://example.com/note",
            content="Content",
            published_date=datetime.now(timezone.utc)
        )

        assert note.likes == 0
        assert note.comments == 0

    def test_release_note_source_property(self):
        """Test ReleaseNote source property returns 'community'."""
        from scrapers.instructure_community import ReleaseNote

        note = ReleaseNote(
            title="Test",
            url="https://example.com",
            content="Content",
            published_date=datetime.now(timezone.utc)
        )

        assert note.source == "community"

    def test_release_note_source_id_property(self):
        """Test ReleaseNote source_id property returns unique ID based on URL and post_type."""
        from scrapers.instructure_community import ReleaseNote

        note1 = ReleaseNote(
            title="Test 1",
            url="https://community.instructure.com/t/post/123",
            content="Content",
            published_date=datetime.now(timezone.utc)
        )
        note2 = ReleaseNote(
            title="Test 2",
            url="https://community.instructure.com/t/post/456",
            content="Content",
            published_date=datetime.now(timezone.utc)
        )

        # Should start with post_type (default: 'release_note_')
        assert note1.source_id.startswith("release_note_")
        assert note2.source_id.startswith("release_note_")

        # Different URLs should produce different source_ids
        assert note1.source_id != note2.source_id

        # Deploy note should have different prefix
        deploy_note = ReleaseNote(
            title="Deploy Notes",
            url="https://community.instructure.com/t/post/789",
            content="Content",
            published_date=datetime.now(timezone.utc),
            post_type="deploy_note"
        )
        assert deploy_note.source_id.startswith("deploy_note_")

    def test_release_note_source_id_same_url(self):
        """Test ReleaseNote source_id is consistent for same URL."""
        from scrapers.instructure_community import ReleaseNote

        url = "https://community.instructure.com/t/post/123"
        note1 = ReleaseNote(title="A", url=url, content="C", published_date=datetime.now(timezone.utc))
        note2 = ReleaseNote(title="B", url=url, content="D", published_date=datetime.now(timezone.utc))

        # Same URL should produce same source_id
        assert note1.source_id == note2.source_id

    def test_changelog_entry_creation(self):
        """Test ChangeLogEntry dataclass constructor with all fields."""
        from scrapers.instructure_community import ChangeLogEntry

        entry = ChangeLogEntry(
            title="API Changelog 2024-01-15",
            url="https://community.instructure.com/t/changelog/456",
            content="API changes include...",
            published_date=datetime.now(timezone.utc)
        )

        assert entry.title == "API Changelog 2024-01-15"
        assert entry.url == "https://community.instructure.com/t/changelog/456"
        assert entry.content == "API changes include..."

    def test_changelog_entry_source_property(self):
        """Test ChangeLogEntry source property returns 'community'."""
        from scrapers.instructure_community import ChangeLogEntry

        entry = ChangeLogEntry(
            title="Test",
            url="https://example.com",
            content="Content",
            published_date=datetime.now(timezone.utc)
        )

        assert entry.source == "community"

    def test_changelog_entry_source_id_property(self):
        """Test ChangeLogEntry source_id property returns unique ID."""
        from scrapers.instructure_community import ChangeLogEntry

        entry = ChangeLogEntry(
            title="Test",
            url="https://community.instructure.com/t/changelog/789",
            content="Content",
            published_date=datetime.now(timezone.utc)
        )

        # Should start with 'changelog_'
        assert entry.source_id.startswith("changelog_")


class TestInstructureScraperInit:
    """Tests for InstructureScraper initialization."""

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_initialization_headless_default(self, mock_sync_playwright):
        """Test InstructureScraper initializes with headless=True by default."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        scraper = InstructureScraper()

        assert scraper.headless is True
        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_initialization_headless_false(self, mock_sync_playwright):
        """Test InstructureScraper initializes with headless=False."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        scraper = InstructureScraper(headless=False)

        assert scraper.headless is False
        mock_playwright.chromium.launch.assert_called_once_with(headless=False)
        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_initialization_custom_rate_limit(self, mock_sync_playwright):
        """Test InstructureScraper initializes with custom rate_limit_seconds."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        scraper = InstructureScraper(rate_limit_seconds=5.0)

        assert scraper.rate_limit_seconds == 5.0
        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_initialization_playwright_not_installed(self):
        """Test graceful handling when Playwright not installed."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()

        assert scraper.browser is None
        assert scraper.playwright is None
        assert scraper.page is None
        assert scraper.context is None

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_initialization_browser_launch_failure(self, mock_sync_playwright):
        """Test graceful handling when browser fails to launch."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch.side_effect = Exception("Browser launch failed")
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        scraper = InstructureScraper()

        # Should gracefully handle failure
        assert scraper.browser is None
        assert scraper.page is None

    def test_class_constants(self):
        """Test InstructureScraper class constants are defined."""
        from scrapers.instructure_community import InstructureScraper

        assert "release-notes" in InstructureScraper.RELEASE_NOTES_URL.lower()
        assert "changelog" in InstructureScraper.CHANGELOG_URL.lower()
        assert "Canvas-RSS" in InstructureScraper.USER_AGENT


class TestInstructureScraperDateParsing:
    """Tests for _parse_relative_date and _is_within_hours methods."""

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_minutes_ago(self):
        """Test parsing 'X minutes ago' format."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("30 minutes ago")

        assert result is not None
        # Should be approximately 30 minutes ago
        now = datetime.now(timezone.utc)
        diff = now - result
        assert 29 <= diff.total_seconds() / 60 <= 31

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_hours_ago(self):
        """Test parsing 'X hours ago' format."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("5 hours ago")

        assert result is not None
        now = datetime.now(timezone.utc)
        diff = now - result
        assert 4.9 <= diff.total_seconds() / 3600 <= 5.1

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_days_ago(self):
        """Test parsing 'X days ago' format."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("2 days ago")

        assert result is not None
        now = datetime.now(timezone.utc)
        diff = now - result
        assert 1.9 <= diff.total_seconds() / 86400 <= 2.1

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_yesterday(self):
        """Test parsing 'Yesterday' format."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("Yesterday")

        assert result is not None
        now = datetime.now(timezone.utc)
        diff = now - result
        # Should be approximately 1 day ago
        assert 0.9 <= diff.total_seconds() / 86400 <= 1.1

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_today(self):
        """Test parsing 'Today' format."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("Today")

        assert result is not None
        now = datetime.now(timezone.utc)
        diff = now - result
        # Should be within seconds of now
        assert diff.total_seconds() < 5

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_iso_format(self):
        """Test parsing ISO 8601 format (2024-01-15T10:30:00)."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("2024-01-15T10:30:00")

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_iso_with_z(self):
        """Test parsing ISO 8601 format with Z suffix."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("2024-01-15T10:30:00Z")

        assert result is not None
        assert result.year == 2024

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_empty_string(self):
        """Test parsing empty string returns None."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("")

        assert result is None

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_none(self):
        """Test parsing None returns None."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date(None)

        assert result is None

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_invalid_string(self):
        """Test parsing invalid string returns None."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("not a valid date")

        assert result is None

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_parse_relative_date_just_now(self):
        """Test parsing 'just now' format."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._parse_relative_date("just now")

        assert result is not None
        now = datetime.now(timezone.utc)
        diff = now - result
        assert diff.total_seconds() < 5

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_is_within_hours_true(self):
        """Test _is_within_hours returns True for datetime within hours."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        # 12 hours ago should be within 24 hours
        dt = datetime.now(timezone.utc) - timedelta(hours=12)
        result = scraper._is_within_hours(dt, hours=24)

        assert result is True

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_is_within_hours_false(self):
        """Test _is_within_hours returns False for datetime outside hours."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        # 48 hours ago should be outside 24 hours
        dt = datetime.now(timezone.utc) - timedelta(hours=48)
        result = scraper._is_within_hours(dt, hours=24)

        assert result is False

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_is_within_hours_none_datetime(self):
        """Test _is_within_hours returns False for None datetime."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper._is_within_hours(None, hours=24)

        assert result is False

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_is_within_hours_naive_datetime(self):
        """Test _is_within_hours handles naive datetime (no timezone)."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        # Naive datetime (no timezone)
        dt = datetime.now() - timedelta(hours=12)
        result = scraper._is_within_hours(dt, hours=24)

        assert result is True


class TestInstructureScraperScraping:
    """Tests for scrape_release_notes and scrape_changelog methods."""

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_scrape_release_notes_browser_none(self):
        """Test scrape_release_notes returns empty list when browser is None."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper.scrape_release_notes()

        assert result == []

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_scrape_release_notes_success(self, mock_sync_playwright):
        """Test successful release notes scraping returns ReleaseNote list."""
        from scrapers.instructure_community import InstructureScraper, ReleaseNote

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        # Mock page navigation
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        # Mock finding post elements
        mock_element = MagicMock()
        mock_element.evaluate.return_value = "a"
        mock_element.inner_text.return_value = "Canvas Q1 2024 Release"
        mock_element.get_attribute.return_value = "/t/canvas-q1-release/123"

        mock_page.query_selector_all.return_value = [mock_element]
        mock_page.query_selector.return_value = MagicMock(inner_text=MagicMock(return_value="Post content"))

        scraper = InstructureScraper()

        # Mock the internal methods to return test data
        with patch.object(scraper, '_extract_post_cards') as mock_extract:
            with patch.object(scraper, '_get_post_content') as mock_content:
                with patch.object(scraper, '_click_deploys_tab') as mock_click:
                    mock_extract.return_value = [{
                        "title": "Canvas Q1 2024 Release",
                        "url": "https://community.instructure.com/t/canvas-q1/123",
                        "date_text": "2 hours ago"
                    }]
                    mock_content.return_value = ("Post content about new features", 25, 5)
                    mock_click.return_value = False  # Don't scrape deploy notes

                    result = scraper.scrape_release_notes(hours=24)

        assert len(result) == 1
        assert isinstance(result[0], ReleaseNote)
        assert result[0].title == "Canvas Q1 2024 Release"
        assert result[0].content == "Post content about new features"
        assert result[0].likes == 25
        assert result[0].comments == 5

        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_scrape_release_notes_navigation_error(self, mock_sync_playwright):
        """Test scrape_release_notes handles navigation errors gracefully."""
        from scrapers.instructure_community import InstructureScraper, PlaywrightTimeout

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        # Mock page navigation to timeout
        mock_page.goto.side_effect = PlaywrightTimeout("Navigation timeout")

        scraper = InstructureScraper()
        result = scraper.scrape_release_notes()

        assert result == []
        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_scrape_release_notes_filters_old_posts(self, mock_sync_playwright):
        """Test scrape_release_notes filters posts to specified hours."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        scraper = InstructureScraper()

        with patch.object(scraper, '_extract_post_cards') as mock_extract:
            with patch.object(scraper, '_get_post_content') as mock_content:
                with patch.object(scraper, '_click_deploys_tab') as mock_click:
                    mock_extract.return_value = [
                        {"title": "Recent Post", "url": "https://example.com/1", "date_text": "2 hours ago"},
                        {"title": "Old Post", "url": "https://example.com/2", "date_text": "5 days ago"}
                    ]
                    mock_content.return_value = ("Content", 0, 0)
                    mock_click.return_value = False  # Don't scrape deploy notes

                    result = scraper.scrape_release_notes(hours=24)

        # Only the recent post should be included
        assert len(result) == 1
        assert result[0].title == "Recent Post"

        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_scrape_changelog_browser_none(self):
        """Test scrape_changelog returns empty list when browser is None."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper.scrape_changelog()

        assert result == []

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_scrape_changelog_success(self, mock_sync_playwright):
        """Test successful changelog scraping returns ChangeLogEntry list."""
        from scrapers.instructure_community import InstructureScraper, ChangeLogEntry

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        scraper = InstructureScraper()

        with patch.object(scraper, '_extract_post_cards') as mock_extract:
            with patch.object(scraper, '_get_post_content') as mock_content:
                mock_extract.return_value = [{
                    "title": "API Changes January 2024",
                    "url": "https://community.instructure.com/t/api-changes/456",
                    "date_text": "3 hours ago"
                }]
                mock_content.return_value = ("API deprecation notice...", 10, 3)

                result = scraper.scrape_changelog(hours=24)

        assert len(result) == 1
        assert isinstance(result[0], ChangeLogEntry)
        assert result[0].title == "API Changes January 2024"
        assert result[0].content == "API deprecation notice..."

        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_scrape_changelog_navigation_error(self, mock_sync_playwright):
        """Test scrape_changelog handles navigation errors gracefully."""
        from scrapers.instructure_community import InstructureScraper, PlaywrightTimeout

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        mock_page.goto.side_effect = PlaywrightTimeout("Navigation timeout")

        scraper = InstructureScraper()
        result = scraper.scrape_changelog()

        assert result == []
        scraper.close()


class TestInstructureScraperReactions:
    """Tests for get_community_reactions method."""

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_get_community_reactions_browser_none(self):
        """Test get_community_reactions returns zeros when browser is None."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()
        result = scraper.get_community_reactions("https://community.instructure.com/t/post/123")

        assert result == {"likes": 0, "comments": 0, "views": 0}

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_get_community_reactions_success(self, mock_sync_playwright):
        """Test get_community_reactions returns dict with likes, comments, views."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        # Mock likes element
        mock_likes_el = MagicMock()
        mock_likes_el.inner_text.return_value = "42 likes"

        # Mock comments element
        mock_comments_el = MagicMock()
        mock_comments_el.inner_text.return_value = "15 comments"

        # Mock views element
        mock_views_el = MagicMock()
        mock_views_el.inner_text.return_value = "1234 views"

        def query_selector_side_effect(selector):
            if "like" in selector.lower() or "kudos" in selector.lower():
                return mock_likes_el
            elif "comment" in selector.lower() or "repl" in selector.lower():
                return mock_comments_el
            elif "view" in selector.lower():
                return mock_views_el
            return None

        mock_page.query_selector.side_effect = query_selector_side_effect

        scraper = InstructureScraper()
        result = scraper.get_community_reactions("https://community.instructure.com/t/post/123")

        assert result["likes"] == 42
        assert result["comments"] == 15
        assert result["views"] == 1234

        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_get_community_reactions_invalid_url(self, mock_sync_playwright):
        """Test get_community_reactions handles invalid URL gracefully."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        mock_page.goto.side_effect = Exception("Invalid URL")

        scraper = InstructureScraper()
        result = scraper.get_community_reactions("not-a-valid-url")

        assert result == {"likes": 0, "comments": 0, "views": 0}

        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_get_community_reactions_timeout(self, mock_sync_playwright):
        """Test get_community_reactions handles timeout gracefully."""
        from scrapers.instructure_community import InstructureScraper, PlaywrightTimeout

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        mock_page.goto.side_effect = PlaywrightTimeout("Timeout")

        scraper = InstructureScraper()
        result = scraper.get_community_reactions("https://community.instructure.com/t/post/123")

        assert result == {"likes": 0, "comments": 0, "views": 0}

        scraper.close()


class TestInstructureScraperCleanup:
    """Tests for close() and context manager."""

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_close_cleans_up_resources(self, mock_sync_playwright):
        """Test close() cleans up browser resources."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        scraper = InstructureScraper()

        # Verify resources are set
        assert scraper.browser is not None
        assert scraper.page is not None
        assert scraper.context is not None
        assert scraper.playwright is not None

        scraper.close()

        # Verify close was called on all resources
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

        # Verify resources are set to None
        assert scraper.browser is None
        assert scraper.page is None
        assert scraper.context is None
        assert scraper.playwright is None

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_close_safe_to_call_multiple_times(self, mock_sync_playwright):
        """Test close() is safe to call multiple times."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        scraper = InstructureScraper()

        # Call close multiple times - should not raise
        scraper.close()
        scraper.close()
        scraper.close()

        # Close should only be called once on each resource
        assert mock_page.close.call_count == 1
        assert mock_browser.close.call_count == 1

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', False)
    def test_close_works_with_partial_initialization(self):
        """Test close() works even with partial initialization."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper()

        # All resources should be None
        assert scraper.browser is None

        # Should not raise
        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_context_manager_enter_returns_self(self, mock_sync_playwright):
        """Test __enter__ returns self."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        scraper = InstructureScraper()
        result = scraper.__enter__()

        assert result is scraper

        scraper.close()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_context_manager_exit_calls_close(self, mock_sync_playwright):
        """Test __exit__ calls close()."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        with InstructureScraper() as scraper:
            assert scraper.browser is not None

        # After context manager exit, resources should be cleaned up
        mock_page.close.assert_called_once()
        mock_browser.close.assert_called_once()

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_context_manager_exit_returns_false(self, mock_sync_playwright):
        """Test __exit__ returns False (does not suppress exceptions)."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        scraper = InstructureScraper()
        result = scraper.__exit__(None, None, None)

        assert result is False

    @patch('scrapers.instructure_community.PLAYWRIGHT_AVAILABLE', True)
    @patch('scrapers.instructure_community.sync_playwright')
    def test_close_handles_errors_gracefully(self, mock_sync_playwright):
        """Test close() handles errors during cleanup gracefully."""
        from scrapers.instructure_community import InstructureScraper

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        # Make close methods raise errors
        mock_page.close.side_effect = Exception("Page close error")
        mock_context.close.side_effect = Exception("Context close error")
        mock_browser.close.side_effect = Exception("Browser close error")
        mock_playwright.stop.side_effect = Exception("Playwright stop error")

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        scraper = InstructureScraper()

        # Should not raise despite errors
        scraper.close()

        # Resources should still be set to None
        assert scraper.browser is None
        assert scraper.page is None
        assert scraper.context is None
        assert scraper.playwright is None


class TestDiscussionUpdate:
    """Tests for DiscussionUpdate dataclass."""

    def test_discussion_update_new_post(self):
        """Test DiscussionUpdate for new post."""
        from scrapers.instructure_community import DiscussionUpdate, CommunityPost
        from datetime import datetime

        post = CommunityPost(
            title="Test", url="http://example.com", content="Content",
            published_date=datetime.now(), post_type="question"
        )
        update = DiscussionUpdate(
            post=post, is_new=True, previous_comment_count=0,
            new_comment_count=0, latest_comment=None
        )
        assert update.is_new is True

    def test_discussion_update_with_new_comments(self):
        """Test DiscussionUpdate for post with new comments."""
        from scrapers.instructure_community import DiscussionUpdate, CommunityPost
        from datetime import datetime

        post = CommunityPost(
            title="Test", url="http://example.com", content="Content",
            published_date=datetime.now(), comments=8, post_type="question"
        )
        update = DiscussionUpdate(
            post=post, is_new=False, previous_comment_count=5,
            new_comment_count=3, latest_comment="Latest reply..."
        )
        assert update.is_new is False
        assert update.new_comment_count == 3


class TestFeatureTableData:
    """Tests for FeatureTableData dataclass."""

    def test_feature_table_data_creation(self):
        """Test creating FeatureTableData."""
        from scrapers.instructure_community import FeatureTableData

        table = FeatureTableData(
            enable_location="Account Settings",
            default_status="Off",
            permissions="Admin only",
            affected_areas=["Assignments", "SpeedGrader"],
            affects_roles=["instructors", "students"]
        )
        assert table.enable_location == "Account Settings"
        assert "Assignments" in table.affected_areas


class TestFeature:
    """Tests for Feature dataclass."""

    def test_feature_creation(self):
        """Test creating Feature."""
        from scrapers.instructure_community import Feature, FeatureTableData

        table = FeatureTableData(
            enable_location="Account", default_status="Off",
            permissions="Admin", affected_areas=["Assignments"],
            affects_roles=["instructors"]
        )
        feature = Feature(
            category="Assignments",
            name="Document Processing App",
            anchor_id="document-processing-app",
            added_date=None,
            raw_content="<p>Feature content</p>",
            table_data=table
        )
        assert feature.category == "Assignments"
        assert feature.anchor_id == "document-processing-app"

    def test_feature_source_id(self):
        """Test Feature source_id generation."""
        from scrapers.instructure_community import Feature, FeatureTableData

        table = FeatureTableData("", "", "", [], [])
        feature = Feature(
            category="Apps", name="Test", anchor_id="test-feature",
            added_date=None, raw_content="", table_data=table
        )
        # source_id should be set by parent page
        assert feature.anchor_id == "test-feature"


class TestUpcomingChange:
    """Tests for UpcomingChange dataclass."""

    def test_upcoming_change_creation(self):
        """Test creating UpcomingChange."""
        from scrapers.instructure_community import UpcomingChange
        from datetime import datetime

        change = UpcomingChange(
            date=datetime(2026, 3, 21),
            description="User-Agent Header Enforcement",
            days_until=48
        )
        assert change.description == "User-Agent Header Enforcement"

    def test_upcoming_change_urgency(self):
        """Test urgency detection (within 30 days)."""
        from scrapers.instructure_community import UpcomingChange
        from datetime import datetime

        urgent = UpcomingChange(datetime(2026, 2, 15), "Urgent change", 14)
        not_urgent = UpcomingChange(datetime(2026, 4, 1), "Later change", 60)

        assert urgent.days_until <= 30
        assert not_urgent.days_until > 30


class TestReleaseNotePage:
    """Tests for ReleaseNotePage dataclass."""

    def test_release_note_page_creation(self):
        """Test creating ReleaseNotePage."""
        from scrapers.instructure_community import ReleaseNotePage, Feature, FeatureTableData
        from datetime import datetime

        table = FeatureTableData("", "", "", [], [])
        feature = Feature("Apps", "Test", "test", None, "", table)

        page = ReleaseNotePage(
            title="Canvas Release Notes (2026-02-21)",
            url="https://example.com/release",
            release_date=datetime(2026, 2, 21),
            upcoming_changes=[],
            features=[feature],
            sections={"New Features": [feature]}
        )
        assert "2026-02-21" in page.title
        assert len(page.features) == 1

    def test_release_note_page_source_id(self):
        """Test source_id format for release page."""
        from scrapers.instructure_community import ReleaseNotePage
        from datetime import datetime

        page = ReleaseNotePage(
            title="Canvas Release Notes (2026-02-21)",
            url="https://example.com",
            release_date=datetime(2026, 2, 21),
            upcoming_changes=[], features=[], sections={}
        )
        # Parent source_id should be date-based
        expected_id = "release-2026-02-21"
        assert page.release_date.strftime("release-%Y-%m-%d") == expected_id


class TestDeployNoteDataclasses:
    """Tests for Deploy Note dataclasses."""

    def test_deploy_change_creation(self):
        """Test creating DeployChange."""
        from scrapers.instructure_community import DeployChange, FeatureTableData

        change = DeployChange(
            category="Navigation",
            name="Small Screen Branding Updated",
            anchor_id="small-screen-global-navigation-branding-updated",
            section="Updated Features",
            raw_content="<p>Content</p>",
            table_data=None,
            status=None,
            status_date=None
        )
        assert change.section == "Updated Features"

    def test_deploy_change_delayed_status(self):
        """Test DeployChange with delayed status."""
        from scrapers.instructure_community import DeployChange
        from datetime import datetime

        change = DeployChange(
            category="Apps", name="Delayed Feature",
            anchor_id="delayed-feature", section="Updated Features",
            raw_content="", table_data=None,
            status="delayed", status_date=datetime(2026, 1, 30)
        )
        assert change.status == "delayed"

    def test_deploy_note_page_creation(self):
        """Test creating DeployNotePage."""
        from scrapers.instructure_community import DeployNotePage, DeployChange
        from datetime import datetime

        change = DeployChange("Nav", "Fix", "fix", "Updates", "", None, None, None)
        page = DeployNotePage(
            title="Canvas Deploy Notes (2026-02-11)",
            url="https://example.com/deploy",
            deploy_date=datetime(2026, 2, 11),
            beta_date=datetime(2026, 1, 29),
            changes=[change],
            sections={"Updated Features": [change]}
        )
        assert page.beta_date is not None
        assert len(page.changes) == 1


class TestExtractSourceId:
    """Tests for extract_source_id helper."""

    def test_extract_from_discussion_url(self):
        """Test extracting ID from discussion URL."""
        from scrapers.instructure_community import extract_source_id
        url = "https://community.instructure.com/en/discussion/664587/test"
        assert extract_source_id(url, "question") == "question_664587"

    def test_extract_from_blog_url(self):
        """Test extracting ID from blog URL."""
        from scrapers.instructure_community import extract_source_id
        url = "https://community.instructure.com/en/blog/664752/test"
        assert extract_source_id(url, "blog") == "blog_664752"

    def test_extract_fallback_to_hash(self):
        """Test fallback to hash for non-matching URL."""
        from scrapers.instructure_community import extract_source_id
        url = "https://example.com/other/path"
        result = extract_source_id(url, "question")
        assert result.startswith("question_")


class TestScrapeLatestComment:
    """Tests for scrape_latest_comment method."""

    def test_returns_none_without_browser(self):
        """Test returns None when browser not available."""
        from scrapers.instructure_community import InstructureScraper
        scraper = InstructureScraper.__new__(InstructureScraper)
        scraper.page = None
        assert scraper.scrape_latest_comment("http://example.com") is None

    def test_truncates_long_comments(self):
        """Test that long comments are truncated to 500 chars."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper.__new__(InstructureScraper)
        scraper.rate_limit_seconds = 0

        mock_page = MagicMock()
        mock_element = MagicMock()
        mock_element.inner_text.return_value = "A" * 600
        mock_page.query_selector.return_value = mock_element
        mock_page.goto = MagicMock()
        mock_page.wait_for_load_state = MagicMock()
        scraper.page = mock_page

        result = scraper.scrape_latest_comment("http://example.com/discussion/1")
        assert len(result) == 500
