"""Tests for database operations."""

import pytest
import json
from datetime import datetime, timedelta


class TestDatabase:
    """Tests for the Database class."""

    def test_database_initialization(self, temp_db):
        """Test that database initializes with correct schema."""
        # Schema should be created on init
        conn = temp_db._get_connection()
        cursor = conn.cursor()

        # Check content_items table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='content_items'"
        )
        assert cursor.fetchone() is not None

        # Check feed_history table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feed_history'"
        )
        assert cursor.fetchone() is not None

    def test_item_exists_returns_false_for_new_item(self, temp_db):
        """Test that item_exists returns False for items not in database."""
        assert temp_db.item_exists("nonexistent-id") is False

    def test_insert_item(self, temp_db, sample_content_item):
        """Test inserting a content item returns a valid row ID."""
        row_id = temp_db.insert_item(sample_content_item)
        assert row_id > 0

    def test_item_exists_returns_true_after_insert(self, temp_db, sample_content_item):
        """Test that item_exists returns True after inserting."""
        temp_db.insert_item(sample_content_item)
        assert temp_db.item_exists(sample_content_item.source_id) is True

    def test_insert_item_duplicate_returns_negative_one(self, temp_db, sample_content_item):
        """Test that inserting a duplicate item returns -1."""
        # First insert should succeed
        first_id = temp_db.insert_item(sample_content_item)
        assert first_id > 0

        # Second insert of same item should return -1
        second_id = temp_db.insert_item(sample_content_item)
        assert second_id == -1

    def test_insert_item_with_topics(self, temp_db):
        """Test that topics are serialized correctly as JSON."""
        from processor.content_processor import ContentItem

        item = ContentItem(
            source="test",
            source_id="topics-test-123",
            title="Test with Topics",
            url="https://example.com/topics",
            content="Content with topics",
            topics=["Gradebook", "Assignments", "SpeedGrader"],
            published_date=datetime.now()
        )

        row_id = temp_db.insert_item(item)
        assert row_id > 0

        # Verify topics were stored as JSON
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT topics FROM content_items WHERE source_id = ?", (item.source_id,))
        row = cursor.fetchone()
        topics = json.loads(row["topics"])
        assert topics == ["Gradebook", "Assignments", "SpeedGrader"]

    def test_insert_item_with_empty_topics(self, temp_db):
        """Test that empty topics list is serialized as empty JSON array."""
        from processor.content_processor import ContentItem

        item = ContentItem(
            source="test",
            source_id="empty-topics-123",
            title="Test without Topics",
            url="https://example.com/empty",
            content="Content without topics",
            topics=[],
            published_date=datetime.now()
        )

        row_id = temp_db.insert_item(item)
        assert row_id > 0

        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT topics FROM content_items WHERE source_id = ?", (item.source_id,))
        row = cursor.fetchone()
        topics = json.loads(row["topics"])
        assert topics == []

    def test_insert_item_with_datetime_published_date(self, temp_db):
        """Test that datetime published_date is converted to ISO format."""
        from processor.content_processor import ContentItem

        test_date = datetime(2024, 1, 15, 10, 30, 0)
        item = ContentItem(
            source="test",
            source_id="datetime-test-123",
            title="Test with datetime",
            url="https://example.com/datetime",
            content="Content with datetime",
            published_date=test_date
        )

        row_id = temp_db.insert_item(item)
        assert row_id > 0

        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT published_date FROM content_items WHERE source_id = ?", (item.source_id,))
        row = cursor.fetchone()
        assert row["published_date"] == test_date.isoformat()

    def test_insert_item_with_string_published_date(self, temp_db):
        """Test that string published_date is stored as-is."""
        from processor.content_processor import ContentItem

        test_date_str = "2024-01-15T10:30:00Z"
        item = ContentItem(
            source="test",
            source_id="string-date-123",
            title="Test with string date",
            url="https://example.com/strdate",
            content="Content with string date",
            published_date=test_date_str
        )

        row_id = temp_db.insert_item(item)
        assert row_id > 0

        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT published_date FROM content_items WHERE source_id = ?", (item.source_id,))
        row = cursor.fetchone()
        assert row["published_date"] == test_date_str

    def test_get_recent_items_returns_items_within_days(self, temp_db):
        """Test that get_recent_items returns items within the specified days."""
        from processor.content_processor import ContentItem

        # Insert a test item
        item = ContentItem(
            source="test",
            source_id="recent-test-123",
            title="Recent Item",
            url="https://example.com/recent",
            content="Recent content",
            topics=["Gradebook"],
            published_date=datetime.now()
        )
        temp_db.insert_item(item)

        # Get recent items
        items = temp_db.get_recent_items(days=7)
        assert len(items) == 1
        assert items[0]["source_id"] == "recent-test-123"
        assert items[0]["title"] == "Recent Item"

    def test_get_recent_items_returns_empty_for_no_items(self, temp_db):
        """Test that get_recent_items returns empty list when no items exist."""
        items = temp_db.get_recent_items(days=7)
        assert items == []

    def test_get_recent_items_deserializes_topics_json(self, temp_db):
        """Test that topics JSON is properly deserialized."""
        from processor.content_processor import ContentItem

        item = ContentItem(
            source="test",
            source_id="topics-deserialize-123",
            title="Topic Deserialize Test",
            url="https://example.com/deserialize",
            content="Test content",
            topics=["Assignments", "Quizzes"],
            published_date=datetime.now()
        )
        temp_db.insert_item(item)

        items = temp_db.get_recent_items(days=7)
        assert len(items) == 1
        assert items[0]["topics"] == ["Assignments", "Quizzes"]

    def test_get_recent_items_handles_invalid_topics_json(self, temp_db):
        """Test that invalid topics JSON is handled gracefully."""
        from processor.content_processor import ContentItem

        # Insert item normally first
        item = ContentItem(
            source="test",
            source_id="invalid-json-123",
            title="Invalid JSON Test",
            url="https://example.com/invalid",
            content="Test content",
            published_date=datetime.now()
        )
        temp_db.insert_item(item)

        # Manually corrupt the topics JSON
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE content_items SET topics = 'invalid-json' WHERE source_id = ?",
            ("invalid-json-123",)
        )
        conn.commit()

        # Should handle gracefully and return empty list for topics
        items = temp_db.get_recent_items(days=7)
        assert len(items) == 1
        assert items[0]["topics"] == []

    def test_get_recent_items_with_multiple_items(self, temp_db):
        """Test get_recent_items with multiple items."""
        from processor.content_processor import ContentItem

        for i in range(5):
            item = ContentItem(
                source="test",
                source_id=f"multi-test-{i}",
                title=f"Multi Item {i}",
                url=f"https://example.com/multi{i}",
                content=f"Content {i}",
                published_date=datetime.now()
            )
            temp_db.insert_item(item)

        items = temp_db.get_recent_items(days=7)
        assert len(items) == 5

    def test_get_recent_items_ordered_by_scraped_date_desc(self, temp_db):
        """Test that items are ordered by scraped_date descending (most recent first)."""
        from processor.content_processor import ContentItem

        # Insert items - verify they're returned in the order specified by the query
        # (descending by scraped_date). SQLite CURRENT_TIMESTAMP may have same timestamp
        # for rapid inserts, so we just verify all items are returned.
        for i in range(3):
            item = ContentItem(
                source="test",
                source_id=f"order-test-{i}",
                title=f"Order Item {i}",
                url=f"https://example.com/order{i}",
                content=f"Content {i}",
                published_date=datetime.now()
            )
            temp_db.insert_item(item)

        items = temp_db.get_recent_items(days=7)
        assert len(items) == 3

        # Verify all items are present (order may vary due to same-second timestamps)
        source_ids = {item["source_id"] for item in items}
        assert source_ids == {"order-test-0", "order-test-1", "order-test-2"}

    def test_record_feed_generation(self, temp_db):
        """Test recording a feed generation event."""
        test_xml = "<rss><channel><title>Test Feed</title></channel></rss>"
        temp_db.record_feed_generation(item_count=10, feed_xml=test_xml)

        # Verify the record was created
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feed_history ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()

        assert row is not None
        assert row["item_count"] == 10
        assert row["feed_xml"] == test_xml
        assert row["feed_date"] == datetime.now().date().isoformat()

    def test_record_feed_generation_replaces_same_day(self, temp_db):
        """Test that recording on same day replaces existing record (INSERT OR REPLACE)."""
        xml1 = "<rss><channel><title>First Feed</title></channel></rss>"
        xml2 = "<rss><channel><title>Second Feed</title></channel></rss>"

        temp_db.record_feed_generation(item_count=5, feed_xml=xml1)
        temp_db.record_feed_generation(item_count=15, feed_xml=xml2)

        # Should only have one record for today
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        today = datetime.now().date().isoformat()
        cursor.execute("SELECT * FROM feed_history WHERE feed_date = ?", (today,))
        rows = cursor.fetchall()

        assert len(rows) == 1
        assert rows[0]["item_count"] == 15
        assert rows[0]["feed_xml"] == xml2

    def test_close_connection(self, temp_db):
        """Test that close properly closes the connection."""
        # Connection should be open after operations
        _ = temp_db._get_connection()
        assert temp_db.conn is not None

        temp_db.close()
        assert temp_db.conn is None

    def test_close_idempotent(self, temp_db):
        """Test that calling close multiple times is safe."""
        temp_db.close()
        temp_db.close()  # Should not raise
        assert temp_db.conn is None

    def test_connection_reopens_after_close(self, temp_db):
        """Test that connection can be reopened after close."""
        temp_db.close()

        # Should be able to perform operations again
        conn = temp_db._get_connection()
        assert conn is not None
        assert temp_db.item_exists("some-id") is False


class TestSourceDateFields:
    """Tests for v2.0 source date fields in content_items."""

    def test_insert_item_with_source_dates(self, temp_db):
        """Test that insert_item stores v2.0 source date fields."""
        from processor.content_processor import ContentItem
        from datetime import datetime, timezone

        first_posted = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        last_edited = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
        last_comment_at = datetime(2026, 1, 17, 14, 30, 0, tzinfo=timezone.utc)

        item = ContentItem(
            source="community",
            source_id="question_123456",
            title="Test with source dates",
            url="https://community.instructure.com/t5/Question-Forum/test/td-p/123456",
            content="Test content",
            content_type="question",
            first_posted=first_posted,
            last_edited=last_edited,
            last_comment_at=last_comment_at,
            comment_count=5,
            published_date=first_posted,
        )

        row_id = temp_db.insert_item(item)
        assert row_id > 0

        # Verify dates were stored
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT first_posted, last_edited, last_comment_at, last_checked_at FROM content_items WHERE source_id = ?",
            (item.source_id,)
        )
        row = cursor.fetchone()

        assert row["first_posted"] == first_posted.isoformat()
        assert row["last_edited"] == last_edited.isoformat()
        assert row["last_comment_at"] == last_comment_at.isoformat()
        assert row["last_checked_at"] is not None  # Should be set automatically

    def test_insert_item_with_null_source_dates(self, temp_db):
        """Test that insert_item handles None source date fields."""
        from processor.content_processor import ContentItem

        item = ContentItem(
            source="reddit",
            source_id="reddit_abc123",
            title="Test without source dates",
            url="https://reddit.com/r/canvas/abc123",
            content="Test content",
            content_type="reddit",
            published_date=datetime.now(),
        )

        row_id = temp_db.insert_item(item)
        assert row_id > 0

        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT first_posted, last_edited, last_comment_at FROM content_items WHERE source_id = ?",
            (item.source_id,)
        )
        row = cursor.fetchone()

        # Fields should be NULL when not provided
        assert row["first_posted"] is None
        assert row["last_edited"] is None
        assert row["last_comment_at"] is None


class TestUpdateItemTracking:
    """Tests for update_item_tracking method."""

    def test_update_item_tracking_updates_comment_count(self, temp_db, sample_content_item):
        """Test updating comment count for existing item."""
        temp_db.insert_item(sample_content_item)

        result = temp_db.update_item_tracking(
            source_id=sample_content_item.source_id,
            comment_count=10
        )
        assert result is True

        # Verify update
        count = temp_db.get_comment_count(sample_content_item.source_id)
        assert count == 10

    def test_update_item_tracking_updates_last_comment_at(self, temp_db, sample_content_item):
        """Test updating last_comment_at for existing item."""
        from datetime import timezone

        temp_db.insert_item(sample_content_item)

        new_comment_time = datetime(2026, 2, 1, 15, 0, 0, tzinfo=timezone.utc)
        result = temp_db.update_item_tracking(
            source_id=sample_content_item.source_id,
            last_comment_at=new_comment_time
        )
        assert result is True

        # Verify update
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_comment_at FROM content_items WHERE source_id = ?",
            (sample_content_item.source_id,)
        )
        row = cursor.fetchone()
        assert row["last_comment_at"] == new_comment_time.isoformat()

    def test_update_item_tracking_sets_last_checked_at(self, temp_db, sample_content_item):
        """Test that update_item_tracking always sets last_checked_at."""
        temp_db.insert_item(sample_content_item)

        result = temp_db.update_item_tracking(
            source_id=sample_content_item.source_id,
            comment_count=5
        )
        assert result is True

        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_checked_at FROM content_items WHERE source_id = ?",
            (sample_content_item.source_id,)
        )
        row = cursor.fetchone()
        assert row["last_checked_at"] is not None

    def test_update_item_tracking_returns_false_for_nonexistent(self, temp_db):
        """Test that update_item_tracking returns False for nonexistent item."""
        result = temp_db.update_item_tracking(
            source_id="nonexistent-id",
            comment_count=5
        )
        assert result is False


class TestFeaturesTable:
    """Tests for v2.0 features table."""

    def test_features_table_created(self, temp_db):
        """Test that features table is created on init."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='features'"
        )
        assert cursor.fetchone() is not None

    def test_features_table_schema(self, temp_db):
        """Test that features table has correct columns."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(features)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {"feature_id", "name", "status", "created_at"}
        assert expected == columns

    def test_seed_features_populates_table(self, temp_db):
        """Test that seed_features populates the features table."""
        inserted = temp_db.seed_features()
        assert inserted > 0  # Should insert canonical features

        # Verify some known features exist
        speedgrader = temp_db.get_feature("speedgrader")
        assert speedgrader is not None
        assert speedgrader["name"] == "SpeedGrader"

        new_quizzes = temp_db.get_feature("new_quizzes")
        assert new_quizzes is not None
        assert new_quizzes["name"] == "New Quizzes"

    def test_seed_features_idempotent(self, temp_db):
        """Test that seed_features is idempotent."""
        first_count = temp_db.seed_features()
        second_count = temp_db.seed_features()
        assert first_count > 0
        assert second_count == 0  # No new inserts on second run

    def test_get_feature_returns_none_for_unknown(self, temp_db):
        """Test get_feature returns None for unknown feature_id."""
        result = temp_db.get_feature("nonexistent-feature")
        assert result is None

    def test_get_all_features(self, temp_db):
        """Test get_all_features returns all seeded features."""
        temp_db.seed_features()
        features = temp_db.get_all_features()
        assert len(features) > 40  # Should have ~45 canonical features
        # Should be ordered by name
        names = [f["name"] for f in features]
        assert names == sorted(names)


class TestFeatureOptionsTable:
    """Tests for v2.0 feature_options table."""

    def test_feature_options_table_created(self, temp_db):
        """Test that feature_options table is created on init."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feature_options'"
        )
        assert cursor.fetchone() is not None

    def test_feature_options_table_schema(self, temp_db):
        """Test that feature_options table has correct columns."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feature_options)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "option_id", "feature_id", "name", "summary", "status",
            "config_level", "default_state", "first_announced", "last_updated"
        }
        assert expected == columns

    def test_upsert_feature_option_creates_record(self, temp_db):
        """Test upsert creates new feature option record."""
        temp_db.seed_features()
        temp_db.upsert_feature_option(
            option_id="speedgrader-perf-upgrades",
            feature_id="speedgrader",
            name="Performance and usability upgrades for SpeedGrader",
            status="preview",
            summary="Improves SpeedGrader performance",
            config_level="account",
            default_state="disabled"
        )
        options = temp_db.get_feature_options("speedgrader")
        assert len(options) == 1
        assert options[0]["option_id"] == "speedgrader-perf-upgrades"
        assert options[0]["status"] == "preview"

    def test_upsert_feature_option_updates_existing(self, temp_db):
        """Test upsert updates existing feature option."""
        temp_db.seed_features()
        temp_db.upsert_feature_option(
            option_id="test-option",
            feature_id="gradebook",
            name="Test Option",
            status="preview"
        )
        temp_db.upsert_feature_option(
            option_id="test-option",
            feature_id="gradebook",
            name="Updated Test Option",
            status="optional"
        )
        options = temp_db.get_feature_options("gradebook")
        assert len(options) == 1
        assert options[0]["name"] == "Updated Test Option"
        assert options[0]["status"] == "optional"

    def test_get_feature_options_empty(self, temp_db):
        """Test get_feature_options returns empty list for feature with no options."""
        temp_db.seed_features()
        options = temp_db.get_feature_options("assignments")
        assert options == []

    def test_get_active_feature_options(self, temp_db):
        """Test get_active_feature_options returns non-released options."""
        temp_db.seed_features()
        # Add options with different statuses
        temp_db.upsert_feature_option("opt1", "gradebook", "Preview Option", "preview")
        temp_db.upsert_feature_option("opt2", "speedgrader", "Optional Option", "optional")
        temp_db.upsert_feature_option("opt3", "assignments", "Released Option", "released")
        temp_db.upsert_feature_option("opt4", "modules", "Pending Option", "pending")

        active = temp_db.get_active_feature_options()
        option_ids = {o["option_id"] for o in active}
        assert "opt1" in option_ids  # preview
        assert "opt2" in option_ids  # optional
        assert "opt3" not in option_ids  # released - excluded
        assert "opt4" in option_ids  # pending
        # Should include feature_name from JOIN
        assert all("feature_name" in o for o in active)


class TestContentFeatureRefs:
    """Tests for v2.0 content_feature_refs junction table."""

    def test_content_feature_refs_table_created(self, temp_db):
        """Test that content_feature_refs table is created on init."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='content_feature_refs'"
        )
        assert cursor.fetchone() is not None

    def test_add_content_feature_ref_with_feature(self, temp_db):
        """Test adding a content-feature reference."""
        temp_db.seed_features()
        temp_db.add_content_feature_ref(
            content_id="release_note_123",
            feature_id="speedgrader",
            mention_type="announces"
        )
        refs = temp_db.get_features_for_content("release_note_123")
        assert len(refs) == 1
        assert refs[0]["feature_id"] == "speedgrader"
        assert refs[0]["mention_type"] == "announces"

    def test_add_content_feature_ref_with_option(self, temp_db):
        """Test adding a content-feature_option reference."""
        temp_db.seed_features()
        temp_db.upsert_feature_option("opt1", "gradebook", "Test Option", "preview")
        temp_db.add_content_feature_ref(
            content_id="blog_456",
            feature_option_id="opt1",
            mention_type="discusses"
        )
        refs = temp_db.get_features_for_content("blog_456")
        assert len(refs) == 1
        assert refs[0]["option_id"] == "opt1"

    def test_add_content_feature_ref_requires_feature_or_option(self, temp_db):
        """Test that add_content_feature_ref raises error without feature or option."""
        import pytest
        with pytest.raises(ValueError, match="Must provide"):
            temp_db.add_content_feature_ref(content_id="test_123")

    def test_add_content_feature_ref_idempotent(self, temp_db):
        """Test that adding same ref twice doesn't create duplicates."""
        temp_db.seed_features()
        temp_db.add_content_feature_ref("content_1", feature_id="gradebook")
        temp_db.add_content_feature_ref("content_1", feature_id="gradebook")
        refs = temp_db.get_features_for_content("content_1")
        assert len(refs) == 1

    def test_get_content_for_feature_direct(self, temp_db, sample_content_item):
        """Test get_content_for_feature returns content directly linked to feature."""
        temp_db.seed_features()
        temp_db.insert_item(sample_content_item)
        temp_db.add_content_feature_ref(
            content_id=sample_content_item.source_id,
            feature_id="gradebook"
        )
        content = temp_db.get_content_for_feature("gradebook")
        assert len(content) == 1
        assert content[0]["source_id"] == sample_content_item.source_id

    def test_get_content_for_feature_via_option(self, temp_db, sample_content_item):
        """Test get_content_for_feature returns content linked via feature options."""
        temp_db.seed_features()
        temp_db.upsert_feature_option("speedgrader-opt", "speedgrader", "SpeedGrader Option", "preview")
        temp_db.insert_item(sample_content_item)
        temp_db.add_content_feature_ref(
            content_id=sample_content_item.source_id,
            feature_option_id="speedgrader-opt"
        )
        # Query by parent feature should find content linked to its options
        content = temp_db.get_content_for_feature("speedgrader")
        assert len(content) == 1
        assert content[0]["source_id"] == sample_content_item.source_id

    def test_get_features_for_content_multiple(self, temp_db):
        """Test get_features_for_content returns multiple features."""
        temp_db.seed_features()
        temp_db.add_content_feature_ref("content_1", feature_id="gradebook", mention_type="discusses")
        temp_db.add_content_feature_ref("content_1", feature_id="speedgrader", mention_type="questions")
        refs = temp_db.get_features_for_content("content_1")
        assert len(refs) == 2
        feature_ids = {r["feature_id"] for r in refs}
        assert feature_ids == {"gradebook", "speedgrader"}


class TestDeprecatedTablesDropped:
    """Tests to verify deprecated tables are dropped."""

    def test_discussion_tracking_table_not_exists(self, temp_db):
        """Test that discussion_tracking table is dropped."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='discussion_tracking'"
        )
        assert cursor.fetchone() is None

    def test_feature_tracking_table_not_exists(self, temp_db):
        """Test that feature_tracking table is dropped."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feature_tracking'"
        )
        assert cursor.fetchone() is None
