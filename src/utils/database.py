"""SQLite database for deduplication and history."""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from src.processor.content_processor import ContentItem


class Database:
    """SQLite database wrapper for content storage and deduplication."""

    def __init__(self, db_path: str = "data/canvas_digest.db"):
        """Initialize database connection."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def _init_schema(self) -> None:
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Content items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_items (
                id INTEGER PRIMARY KEY,
                source TEXT NOT NULL,
                source_id TEXT UNIQUE,
                url TEXT,
                title TEXT,
                content TEXT,
                summary TEXT,
                published_date TIMESTAMP,
                scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sentiment TEXT,
                primary_topic TEXT,
                topics TEXT,
                engagement_score INTEGER,
                comment_count INTEGER DEFAULT 0,
                content_type TEXT,
                included_in_feed BOOLEAN DEFAULT FALSE
            )
        """)

        # Migration: Add primary_topic column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE content_items ADD COLUMN primary_topic TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            # Column already exists, ignore
            pass

        # Migration: Add comment_count column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE content_items ADD COLUMN comment_count INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            # Column already exists, ignore
            pass

        # Migration: Add content_type column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE content_items ADD COLUMN content_type TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            # Column already exists, ignore
            pass

        # Feed history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feed_history (
                id INTEGER PRIMARY KEY,
                feed_date DATE UNIQUE,
                item_count INTEGER,
                feed_xml TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Discussion tracking table for [NEW]/[UPDATE] badges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discussion_tracking (
                source_id TEXT PRIMARY KEY,
                post_type TEXT NOT NULL,
                comment_count INTEGER DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_checked TEXT NOT NULL
            )
        """)

        # Feature tracking for Release/Deploy notes granular items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_tracking (
                source_id TEXT PRIMARY KEY,
                parent_id TEXT NOT NULL,
                feature_type TEXT NOT NULL,
                anchor_id TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_checked TEXT NOT NULL
            )
        """)

        conn.commit()

    def item_exists(self, source_id: str) -> bool:
        """Check if an item already exists in the database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM content_items WHERE source_id = ?", (source_id,))
        return cursor.fetchone() is not None

    def insert_item(self, item: "ContentItem") -> int:
        """Insert a content item into the database.

        Args:
            item: A ContentItem dataclass instance to store.

        Returns:
            The ID of the inserted row, or -1 if item already exists.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Skip if already exists (deduplication)
        if self.item_exists(item.source_id):
            return -1

        # Serialize topics list as JSON
        topics_json = json.dumps(item.topics) if item.topics else "[]"

        # Handle published_date - could be datetime or string
        published = item.published_date
        if isinstance(published, datetime):
            published = published.isoformat()

        # Get primary_topic (may not exist on older ContentItem instances)
        primary_topic = getattr(item, 'primary_topic', '') or ''

        # Get comment_count and content_type
        comment_count = getattr(item, 'comment_count', 0) or 0
        content_type = getattr(item, 'content_type', '') or ''

        cursor.execute("""
            INSERT INTO content_items
            (source, source_id, url, title, content, summary, published_date,
             sentiment, primary_topic, topics, engagement_score, comment_count,
             content_type, included_in_feed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.source,
            item.source_id,
            item.url,
            item.title,
            item.content,
            item.summary,
            published,
            item.sentiment,
            primary_topic,
            topics_json,
            item.engagement_score,
            comment_count,
            content_type,
            True  # Mark as included in feed
        ))

        conn.commit()
        return cursor.lastrowid

    def get_comment_count(self, source_id: str) -> Optional[int]:
        """Get the stored comment count for an item.

        Args:
            source_id: The unique source ID of the item.

        Returns:
            The comment count, or None if item not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT comment_count FROM content_items WHERE source_id = ?",
            (source_id,)
        )
        row = cursor.fetchone()
        return row["comment_count"] if row else None

    def update_comment_count(self, source_id: str, comment_count: int) -> bool:
        """Update the comment count for an existing item.

        Args:
            source_id: The unique source ID of the item.
            comment_count: The new comment count.

        Returns:
            True if updated, False if item not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE content_items SET comment_count = ? WHERE source_id = ?",
            (comment_count, source_id)
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_recent_items(self, days: int = 7) -> List[dict]:
        """Get items from the last N days.

        Args:
            days: Number of days to look back (default: 7).

        Returns:
            List of dictionaries containing item data.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days)

        cursor.execute("""
            SELECT id, source, source_id, url, title, content, summary,
                   published_date, scraped_date, sentiment, primary_topic,
                   topics, engagement_score, included_in_feed
            FROM content_items
            WHERE scraped_date >= ?
            ORDER BY scraped_date DESC
        """, (cutoff_date.isoformat(),))

        rows = cursor.fetchall()
        items = []

        for row in rows:
            item = dict(row)
            # Parse topics back from JSON
            if item.get("topics"):
                try:
                    item["topics"] = json.loads(item["topics"])
                except json.JSONDecodeError:
                    item["topics"] = []
            else:
                item["topics"] = []
            items.append(item)

        return items

    def record_feed_generation(self, item_count: int, feed_xml: str) -> None:
        """Record a feed generation event.

        Args:
            item_count: Number of items included in the feed.
            feed_xml: The generated RSS XML content.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        today = datetime.now().date().isoformat()

        # Use INSERT OR REPLACE to handle multiple runs on the same day
        cursor.execute("""
            INSERT OR REPLACE INTO feed_history
            (feed_date, item_count, feed_xml, generated_at)
            VALUES (?, ?, ?, ?)
        """, (
            today,
            item_count,
            feed_xml,
            datetime.now().isoformat()
        ))

        conn.commit()

    def get_discussion_tracking(self, source_id: str) -> Optional[dict]:
        """Get tracking data for a discussion post."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source_id, post_type, comment_count, first_seen, last_checked "
            "FROM discussion_tracking WHERE source_id = ?",
            (source_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def upsert_discussion_tracking(
        self, source_id: str, post_type: str, comment_count: int
    ) -> None:
        """Insert or update tracking data for a discussion post."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        existing = self.get_discussion_tracking(source_id)
        if existing:
            cursor.execute(
                "UPDATE discussion_tracking SET comment_count = ?, last_checked = ? WHERE source_id = ?",
                (comment_count, now, source_id)
            )
        else:
            cursor.execute(
                "INSERT INTO discussion_tracking (source_id, post_type, comment_count, first_seen, last_checked) "
                "VALUES (?, ?, ?, ?, ?)",
                (source_id, post_type, comment_count, now, now)
            )
        conn.commit()

    def is_discussion_tracking_empty(self) -> bool:
        """Check if discussion_tracking table is empty (first run)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM discussion_tracking")
        return cursor.fetchone()[0] == 0

    def get_feature_tracking(self, source_id: str) -> Optional[dict]:
        """Get tracking data for a release/deploy feature."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source_id, parent_id, feature_type, anchor_id, first_seen, last_checked "
            "FROM feature_tracking WHERE source_id = ?",
            (source_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def upsert_feature_tracking(
        self, source_id: str, parent_id: str, feature_type: str, anchor_id: str
    ) -> None:
        """Insert or update tracking data for a feature."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        existing = self.get_feature_tracking(source_id)
        if existing:
            cursor.execute(
                "UPDATE feature_tracking SET last_checked = ? WHERE source_id = ?",
                (now, source_id)
            )
        else:
            cursor.execute(
                "INSERT INTO feature_tracking (source_id, parent_id, feature_type, anchor_id, first_seen, last_checked) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (source_id, parent_id, feature_type, anchor_id, now, now)
            )
        conn.commit()

    def get_features_for_parent(self, parent_id: str) -> List[dict]:
        """Get all tracked features for a parent release/deploy."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source_id, parent_id, feature_type, anchor_id, first_seen, last_checked "
            "FROM feature_tracking WHERE parent_id = ?",
            (parent_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def is_feature_tracking_empty(self) -> bool:
        """Check if feature_tracking table is empty (first run)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM feature_tracking")
        return cursor.fetchone()[0] == 0

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
