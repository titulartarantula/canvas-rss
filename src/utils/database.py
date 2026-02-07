"""SQLite database for deduplication and history."""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta, date

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

        # Migration: Add source date columns for v2.0
        for col in ['first_posted', 'last_edited', 'last_comment_at', 'last_checked_at']:
            try:
                cursor.execute(f"ALTER TABLE content_items ADD COLUMN {col} TIMESTAMP")
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

        # Drop deprecated tables from v1.x
        cursor.execute("DROP TABLE IF EXISTS discussion_tracking")
        cursor.execute("DROP TABLE IF EXISTS feature_tracking")

        # Features table (canonical Canvas features)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS features (
                feature_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                llm_generated_at TIMESTAMP
            )
        """)

        # Migration: Add new columns to features if they don't exist
        for col, col_type in [('description', 'TEXT'), ('llm_generated_at', 'TIMESTAMP')]:
            try:
                cursor.execute(f"ALTER TABLE features ADD COLUMN {col} {col_type}")
                conn.commit()
            except sqlite3.OperationalError:
                pass

        # Feature options table (canonical feature options from "Feature Option to Enable")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_options (
                option_id TEXT PRIMARY KEY,
                feature_id TEXT NOT NULL,
                name TEXT NOT NULL,
                canonical_name TEXT,
                description TEXT,
                summary TEXT,
                meta_summary TEXT,
                meta_summary_updated_at TIMESTAMP,
                implementation_status TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                config_level TEXT,
                default_state TEXT,
                user_group_url TEXT,
                beta_date DATE,
                production_date DATE,
                deprecation_date DATE,
                first_announced TIMESTAMP,
                last_updated TIMESTAMP,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                llm_generated_at TIMESTAMP,
                FOREIGN KEY (feature_id) REFERENCES features(feature_id)
            )
        """)

        # Migration: Add new columns to feature_options if they don't exist
        new_option_cols = [
            ('canonical_name', 'TEXT'),
            ('first_seen', 'TEXT'),
            ('last_seen', 'TEXT'),
            ('user_group_url', 'TEXT'),
            ('description', 'TEXT'),
            ('meta_summary', 'TEXT'),
            ('meta_summary_updated_at', 'TIMESTAMP'),
            ('implementation_status', 'TEXT'),
            ('beta_date', 'DATE'),
            ('production_date', 'DATE'),
            ('deprecation_date', 'DATE'),
            ('llm_generated_at', 'TIMESTAMP'),
        ]
        for col, col_type in new_option_cols:
            try:
                cursor.execute(f"ALTER TABLE feature_options ADD COLUMN {col} {col_type}")
                conn.commit()
            except sqlite3.OperationalError:
                pass

        # Content-feature junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_feature_refs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id TEXT NOT NULL,
                feature_id TEXT,
                feature_option_id TEXT,
                mention_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feature_id) REFERENCES features(feature_id),
                FOREIGN KEY (feature_option_id) REFERENCES feature_options(option_id),
                CHECK (feature_id IS NOT NULL OR feature_option_id IS NOT NULL)
            )
        """)
        # Unique index to prevent duplicate refs (treating NULLs as empty strings for uniqueness)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_content_feature_refs_unique
            ON content_feature_refs(content_id, COALESCE(feature_id, ''), COALESCE(feature_option_id, ''))
        """)

        # Create indexes for feature tables
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feature_options_feature ON feature_options(feature_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feature_options_status ON feature_options(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_feature_refs_feature ON content_feature_refs(feature_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_feature_refs_option ON content_feature_refs(feature_option_id)")

        # Feature announcements table (each H4 entry from release/deploy notes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_id TEXT,
                option_id TEXT,
                content_id TEXT NOT NULL,

                -- H4 metadata
                h4_title TEXT NOT NULL,
                anchor_id TEXT,
                section TEXT,
                category TEXT,

                -- Content
                raw_content TEXT,
                description TEXT,
                implications TEXT,
                summary TEXT,

                -- Configuration snapshot at time of announcement
                enable_location_account TEXT,
                enable_location_course TEXT,
                subaccount_config BOOLEAN,
                account_course_setting TEXT,
                permissions TEXT,
                affected_areas TEXT,
                affects_ui BOOLEAN,

                -- Dates
                added_date DATE,
                announced_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Per-announcement lifecycle dates (page-level, not shared via option)
                beta_date DATE,
                production_date DATE,

                FOREIGN KEY (feature_id) REFERENCES features(feature_id),
                FOREIGN KEY (option_id) REFERENCES feature_options(option_id),
                FOREIGN KEY (content_id) REFERENCES content_items(source_id)
            )
        """)

        # Migration: Add feature_id to feature_announcements if it doesn't exist
        try:
            cursor.execute("ALTER TABLE feature_announcements ADD COLUMN feature_id TEXT REFERENCES features(feature_id)")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # Migration: Add per-announcement lifecycle dates
        for col in ('beta_date', 'production_date'):
            try:
                cursor.execute(f"ALTER TABLE feature_announcements ADD COLUMN {col} DATE")
                conn.commit()
            except sqlite3.OperationalError:
                pass

        # Migration: Add description and implications columns to feature_announcements
        for col in ['description', 'implications']:
            try:
                cursor.execute(f"ALTER TABLE feature_announcements ADD COLUMN {col} TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass

        # Indexes for feature_announcements
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_announcements_feature ON feature_announcements(feature_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_announcements_option ON feature_announcements(option_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_announcements_content ON feature_announcements(content_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_announcements_date ON feature_announcements(announced_at)")

        # Upcoming changes table (from "Upcoming Canvas Changes" section)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upcoming_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id TEXT NOT NULL,
                change_date DATE NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (content_id) REFERENCES content_items(source_id)
            )
        """)

        # Indexes for upcoming_changes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_upcoming_content ON upcoming_changes(content_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_upcoming_date ON upcoming_changes(change_date)")

        # Content comments table (for blog/Q&A posts) - NO author field for anonymity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id TEXT NOT NULL,
                comment_text TEXT NOT NULL,
                posted_at TIMESTAMP,
                position INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES content_items(source_id)
            )
        """)

        # Indexes for content_comments
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_content ON content_comments(content_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_posted ON content_comments(posted_at)")

        conn.commit()

        # Migration: Merge feature_options with annotation-polluted option_ids
        self._migrate_merge_annotated_option_ids(conn)

    def _migrate_merge_annotated_option_ids(self, conn):
        """Merge feature_options whose option_id contains bracket annotation slugs.

        Canvas H4 data-id attributes include slugified bracket annotations like
        'canvas-apps-link-added-2026-01-28' that should just be 'canvas-apps-link'.
        This migration merges all annotation variants into a single clean option_id.
        """
        import re

        cursor = conn.cursor()

        # Check if migration already ran (use a simple sentinel)
        cursor.execute(
            "SELECT COUNT(*) FROM feature_options WHERE option_id LIKE '%-added-____-__-__'"
        )
        if cursor.fetchone()[0] == 0:
            # Also check other patterns
            cursor.execute(
                "SELECT COUNT(*) FROM feature_options WHERE option_id LIKE '%-this-feature-is-currently-delayed%'"
            )
            if cursor.fetchone()[0] == 0:
                return  # Nothing to migrate

        annotation_patterns = [
            r'-added-\d{4}-\d{2}-\d{2}$',
            r'-added-on-\d{4}-\d{2}-\d{2}$',
            r'-delayed-as-of-\d{4}-\d{2}-\d{2}$',
            r'-reverted-and-delayed-in-all-environments-as-of-\d{4}-\d{2}-\d{2}$',
            r'-this-feature-is-currently-delayed.*$',
        ]

        cursor.execute("SELECT option_id, feature_id, name, canonical_name, status, "
                        "beta_date, production_date, first_seen, last_seen FROM feature_options")
        all_options = cursor.fetchall()

        # Group dirty option_ids by their clean version
        merge_groups = {}  # clean_id -> [(dirty_id, row_data), ...]
        for row in all_options:
            oid = row[0]
            cleaned = oid
            for p in annotation_patterns:
                cleaned = re.sub(p, '', cleaned)
            if cleaned != oid:
                if cleaned not in merge_groups:
                    merge_groups[cleaned] = []
                merge_groups[cleaned].append(row)

        if not merge_groups:
            return

        for clean_id, dirty_rows in merge_groups.items():
            # Check if clean_id already exists
            cursor.execute("SELECT option_id, feature_id, name, canonical_name, status, "
                            "beta_date, production_date, first_seen, last_seen "
                            "FROM feature_options WHERE option_id = ?", (clean_id,))
            existing = cursor.fetchone()

            # Pick the best name (shortest = without annotations)
            all_rows = list(dirty_rows)
            if existing:
                all_rows.append(existing)

            # Use the shortest name (without annotations) and strip any remaining brackets
            best_name = min((r[2] for r in all_rows), key=len)
            best_name = re.sub(r'\s*\[[^\]]*\]', '', best_name).strip()  # strip brackets
            best_canonical = next((r[3] for r in all_rows if r[3]), None)
            best_feature_id = all_rows[0][1]
            best_beta = next((r[5] for r in all_rows if r[5]), None)
            best_prod = next((r[6] for r in all_rows if r[6]), None)
            earliest_seen = min((r[7] for r in all_rows if r[7]), default=None)
            latest_seen = max((r[8] for r in all_rows if r[8]), default=None)

            dirty_ids = [r[0] for r in dirty_rows]

            if existing:
                # Update the existing clean row with best available data
                cursor.execute("""
                    UPDATE feature_options SET
                        name = COALESCE(?, name),
                        canonical_name = COALESCE(?, canonical_name),
                        beta_date = COALESCE(?, beta_date),
                        production_date = COALESCE(?, production_date),
                        first_seen = CASE WHEN ? < first_seen THEN ? ELSE first_seen END,
                        last_seen = CASE WHEN ? > last_seen THEN ? ELSE last_seen END
                    WHERE option_id = ?
                """, (best_name, best_canonical, best_beta, best_prod,
                      earliest_seen, earliest_seen, latest_seen, latest_seen, clean_id))
            else:
                # Create the clean row from the best dirty data
                cursor.execute("""
                    INSERT INTO feature_options (option_id, feature_id, name, canonical_name,
                        status, beta_date, production_date, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, 'released', ?, ?, ?, ?)
                """, (clean_id, best_feature_id, best_name, best_canonical,
                      best_beta, best_prod, earliest_seen, latest_seen))

            # Re-point feature_announcements from dirty -> clean
            for dirty_id in dirty_ids:
                cursor.execute(
                    "UPDATE feature_announcements SET option_id = ? WHERE option_id = ?",
                    (clean_id, dirty_id))

            # Re-point content_feature_refs from dirty -> clean
            for dirty_id in dirty_ids:
                # Delete refs that would cause unique constraint violations
                cursor.execute("""
                    DELETE FROM content_feature_refs
                    WHERE feature_option_id = ?
                    AND content_id IN (
                        SELECT content_id FROM content_feature_refs
                        WHERE feature_option_id = ?
                    )
                """, (dirty_id, clean_id))
                cursor.execute(
                    "UPDATE content_feature_refs SET feature_option_id = ? WHERE feature_option_id = ?",
                    (clean_id, dirty_id))

            # Delete the dirty feature_options rows
            for dirty_id in dirty_ids:
                cursor.execute("DELETE FROM feature_options WHERE option_id = ?", (dirty_id,))

        # Also clean bracket annotations from any remaining feature_options names
        cursor.execute("SELECT option_id, name FROM feature_options WHERE name LIKE '%[%'")
        for row in cursor.fetchall():
            cleaned_name = re.sub(r'\s*\[[^\]]*\]', '', row[1]).strip()
            if cleaned_name != row[1] and cleaned_name:
                cursor.execute("UPDATE feature_options SET name = ? WHERE option_id = ?",
                               (cleaned_name, row[0]))

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

        # v2.0: Handle source date fields
        first_posted = getattr(item, 'first_posted', None)
        if isinstance(first_posted, datetime):
            first_posted = first_posted.isoformat()

        last_edited = getattr(item, 'last_edited', None)
        if isinstance(last_edited, datetime):
            last_edited = last_edited.isoformat()

        last_comment_at = getattr(item, 'last_comment_at', None)
        if isinstance(last_comment_at, datetime):
            last_comment_at = last_comment_at.isoformat()

        # last_checked_at is set to now when we insert
        last_checked_at = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO content_items
            (source, source_id, url, title, content, summary, published_date,
             sentiment, primary_topic, topics, engagement_score, comment_count,
             content_type, included_in_feed,
             first_posted, last_edited, last_comment_at, last_checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            True,  # Mark as included in feed
            first_posted,
            last_edited,
            last_comment_at,
            last_checked_at,
        ))

        conn.commit()
        return cursor.lastrowid

    def update_item_tracking(
        self,
        source_id: str,
        last_comment_at: datetime = None,
        comment_count: int = None,
        last_checked_at: datetime = None,
    ) -> bool:
        """Update tracking fields for an existing item.

        Use this to update items when re-scraped to track new comments
        or activity without creating duplicate records.

        Args:
            source_id: The unique source ID of the item.
            last_comment_at: New last comment timestamp (optional).
            comment_count: New comment count (optional).
            last_checked_at: When we checked (defaults to now if not provided).

        Returns:
            True if updated, False if item not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build SET clause dynamically based on provided fields
        updates = []
        params = []

        if last_comment_at is not None:
            if isinstance(last_comment_at, datetime):
                last_comment_at = last_comment_at.isoformat()
            updates.append("last_comment_at = ?")
            params.append(last_comment_at)

        if comment_count is not None:
            updates.append("comment_count = ?")
            params.append(comment_count)

        # Always update last_checked_at if any update is being made
        checked_at = last_checked_at or datetime.now()
        if isinstance(checked_at, datetime):
            checked_at = checked_at.isoformat()
        updates.append("last_checked_at = ?")
        params.append(checked_at)

        if not updates:
            return False

        params.append(source_id)
        query = f"UPDATE content_items SET {', '.join(updates)} WHERE source_id = ?"
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0

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

    def seed_features(self) -> int:
        """Seed the features table with canonical Canvas features.

        Returns:
            Number of features inserted.
        """
        from src.constants import CANVAS_FEATURES

        conn = self._get_connection()
        cursor = conn.cursor()
        inserted = 0

        for feature_id, name in CANVAS_FEATURES.items():
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO features (feature_id, name) VALUES (?, ?)",
                    (feature_id, name)
                )
                if cursor.rowcount > 0:
                    inserted += 1
            except sqlite3.Error as e:
                # Log warning but continue with other features
                pass

        conn.commit()
        return inserted

    def get_feature(self, feature_id: str) -> Optional[dict]:
        """Get a feature by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM features WHERE feature_id = ?", (feature_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_features(self) -> List[dict]:
        """Get all features."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM features ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def upsert_feature_option(
        self,
        option_id: str,
        feature_id: str,
        name: str,
        status: str = 'pending',
        canonical_name: str = None,
        summary: str = None,
        config_level: str = None,
        default_state: str = None,
        user_group_url: str = None,
        first_announced: str = None,
    ) -> None:
        """Insert or update a feature option.

        Args:
            option_id: Slugified option ID (e.g., 'document_processor').
            feature_id: FK to features table.
            name: Display name (may be H4 title for backwards compat).
            status: Lifecycle status ('pending', 'preview', 'optional', 'default_on', 'released').
            canonical_name: Exact name from "Feature Option to Enable" table cell.
            summary: Description or raw content excerpt.
            config_level: Where it can be enabled ('account', 'course', 'both').
            default_state: Default status ('enabled', 'disabled').
            user_group_url: URL to Feature Preview community user group (for feedback).
            first_announced: When first announced (ISO timestamp).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO feature_options
                (option_id, feature_id, name, canonical_name, summary, status,
                 config_level, default_state, user_group_url, first_announced,
                 last_updated, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(option_id) DO UPDATE SET
                name = COALESCE(excluded.name, feature_options.name),
                canonical_name = COALESCE(excluded.canonical_name, feature_options.canonical_name),
                summary = COALESCE(excluded.summary, feature_options.summary),
                status = excluded.status,
                config_level = COALESCE(excluded.config_level, feature_options.config_level),
                default_state = COALESCE(excluded.default_state, feature_options.default_state),
                user_group_url = COALESCE(excluded.user_group_url, feature_options.user_group_url),
                last_updated = ?,
                last_seen = ?
        """, (
            option_id, feature_id, name, canonical_name, summary, status,
            config_level, default_state, user_group_url, first_announced, now, now, now, now, now
        ))
        conn.commit()

    def get_feature_options(self, feature_id: str) -> List[dict]:
        """Get all feature options for a feature."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM feature_options WHERE feature_id = ? ORDER BY first_announced DESC",
            (feature_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_active_feature_options(self) -> List[dict]:
        """Get all non-released feature options."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fo.*, f.name as feature_name
            FROM feature_options fo
            JOIN features f ON fo.feature_id = f.feature_id
            WHERE fo.status IN ('pending', 'preview', 'optional', 'default_optional')
            ORDER BY fo.first_announced DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_all_feature_options(self) -> List[dict]:
        """Get all feature options that have canonical names for matching.

        Returns:
            List of dicts with option_id, feature_id, canonical_name, name.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT option_id, feature_id, canonical_name, name
            FROM feature_options
            WHERE canonical_name IS NOT NULL AND canonical_name != ''
            ORDER BY canonical_name
        """)
        return [dict(row) for row in cursor.fetchall()]

    def add_content_feature_ref(
        self,
        content_id: str,
        feature_id: str = None,
        feature_option_id: str = None,
        mention_type: str = 'discusses',
    ) -> None:
        """Link content to a feature or feature option."""
        if not feature_id and not feature_option_id:
            raise ValueError("Must provide feature_id or feature_option_id")

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO content_feature_refs
                (content_id, feature_id, feature_option_id, mention_type)
            VALUES (?, ?, ?, ?)
        """, (content_id, feature_id, feature_option_id, mention_type))
        conn.commit()

    def get_content_for_feature(self, feature_id: str) -> List[dict]:
        """Get all content items related to a feature (direct + via options)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT c.*
            FROM content_items c
            JOIN content_feature_refs r ON c.source_id = r.content_id
            LEFT JOIN feature_options fo ON r.feature_option_id = fo.option_id
            WHERE r.feature_id = ? OR fo.feature_id = ?
            ORDER BY c.scraped_date DESC
        """, (feature_id, feature_id))
        return [dict(row) for row in cursor.fetchall()]

    def get_features_for_content(self, content_id: str) -> List[dict]:
        """Get all features/options referenced by a content item."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                r.mention_type,
                f.feature_id,
                f.name as feature_name,
                fo.option_id,
                fo.name as option_name
            FROM content_feature_refs r
            LEFT JOIN features f ON r.feature_id = f.feature_id
            LEFT JOIN feature_options fo ON r.feature_option_id = fo.option_id
            WHERE r.content_id = ?
        """, (content_id,))
        return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Feature Announcements (H4 entries from release notes)
    # -------------------------------------------------------------------------

    def insert_feature_announcement(
        self,
        content_id: str,
        h4_title: str,
        announced_at: str,
        feature_id: str = None,
        option_id: str = None,
        anchor_id: str = None,
        section: str = None,
        category: str = None,
        raw_content: str = None,
        summary: str = None,
        enable_location_account: str = None,
        enable_location_course: str = None,
        subaccount_config: bool = None,
        account_course_setting: str = None,
        permissions: str = None,
        affected_areas: List[str] = None,
        affects_ui: bool = None,
        added_date: str = None,
    ) -> int:
        """Insert a feature announcement (H4 entry from release/deploy notes).

        Args:
            content_id: FK to content_items.source_id (the release/deploy note).
            h4_title: The H4 headline text.
            announced_at: Release note date (ISO timestamp).
            feature_id: FK to features (from H3 category mapping, nullable).
            option_id: FK to feature_options (from table parsing, nullable).
            anchor_id: data-id for deep linking.
            section: H2 section name (e.g., 'New Features', 'Updated Features').
            category: H3 category name (e.g., 'Assignments', 'Gradebook').
            raw_content: HTML content after H4.
            summary: LLM-generated summary.
            enable_location_account: Account-level config (e.g., 'Disabled/Unlocked').
            enable_location_course: Course-level config (e.g., 'Disabled').
            subaccount_config: Can subaccounts configure?
            account_course_setting: Additional setting name.
            permissions: Permission requirement.
            affected_areas: List of affected Canvas areas.
            affects_ui: Does it affect user interface?
            added_date: From [Added YYYY-MM-DD] annotation.

        Returns:
            The ID of the inserted row.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Serialize affected_areas as JSON
        affected_areas_json = json.dumps(affected_areas) if affected_areas else None

        cursor.execute("""
            INSERT INTO feature_announcements
                (feature_id, option_id, content_id, h4_title, anchor_id, section, category,
                 raw_content, summary, enable_location_account, enable_location_course,
                 subaccount_config, account_course_setting, permissions, affected_areas,
                 affects_ui, added_date, announced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feature_id, option_id, content_id, h4_title, anchor_id, section, category,
            raw_content, summary, enable_location_account, enable_location_course,
            subaccount_config, account_course_setting, permissions, affected_areas_json,
            affects_ui, added_date, announced_at
        ))

        conn.commit()
        return cursor.lastrowid

    def update_announcement_summary(self, content_id: str, anchor_id: str,
                                     description: str = None, implications: str = None) -> bool:
        """Update LLM-generated description and implications for an announcement.

        Args:
            content_id: FK to content_items.source_id.
            anchor_id: The H4 data-id anchor.
            description: LLM-generated 1-2 sentence description.
            implications: LLM-generated 2-3 sentence implications.

        Returns:
            True if a row was updated, False otherwise.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE feature_announcements
            SET description = ?, implications = ?
            WHERE content_id = ? AND anchor_id = ?
        """, (description, implications, content_id, anchor_id))
        conn.commit()
        return cursor.rowcount > 0

    def update_announcement_lifecycle_dates(
        self,
        content_id: str,
        beta_date: Optional[date] = None,
        production_date: Optional[date] = None,
    ) -> int:
        """Update per-announcement lifecycle dates for all announcements on a content page.

        Args:
            content_id: FK to content_items.source_id.
            beta_date: When available in beta environment.
            production_date: When available in production environment.

        Returns:
            Number of rows updated.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE feature_announcements
            SET beta_date = ?, production_date = ?
            WHERE content_id = ?
        """, (
            beta_date.isoformat() if beta_date else None,
            production_date.isoformat() if production_date else None,
            content_id,
        ))
        conn.commit()
        return cursor.rowcount

    def get_announcements_for_option(self, option_id: str) -> List[dict]:
        """Get all announcements for a feature option.

        Args:
            option_id: The feature option ID.

        Returns:
            List of announcement dicts, ordered by announced_at DESC.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fa.*, ci.title as release_note_title, ci.url as release_note_url
            FROM feature_announcements fa
            JOIN content_items ci ON fa.content_id = ci.source_id
            WHERE fa.option_id = ?
            ORDER BY fa.announced_at DESC
        """, (option_id,))

        rows = cursor.fetchall()
        announcements = []
        for row in rows:
            item = dict(row)
            # Parse affected_areas from JSON
            if item.get("affected_areas"):
                try:
                    item["affected_areas"] = json.loads(item["affected_areas"])
                except json.JSONDecodeError:
                    item["affected_areas"] = []
            announcements.append(item)
        return announcements

    def get_announcements_for_feature(self, feature_id: str) -> List[dict]:
        """Get all announcements for a feature (direct or via options).

        Args:
            feature_id: The feature ID.

        Returns:
            List of announcement dicts, ordered by announced_at DESC.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fa.*, ci.title as release_note_title, ci.url as release_note_url,
                   fo.canonical_name, fo.status as option_status
            FROM feature_announcements fa
            JOIN content_items ci ON fa.content_id = ci.source_id
            LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
            WHERE fa.feature_id = ? OR fo.feature_id = ?
            ORDER BY fa.announced_at DESC
        """, (feature_id, feature_id))

        rows = cursor.fetchall()
        announcements = []
        for row in rows:
            item = dict(row)
            if item.get("affected_areas"):
                try:
                    item["affected_areas"] = json.loads(item["affected_areas"])
                except json.JSONDecodeError:
                    item["affected_areas"] = []
            announcements.append(item)
        return announcements

    def get_announcements_for_content(self, content_id: str) -> List[dict]:
        """Get all feature announcements in a release/deploy note.

        Args:
            content_id: The content item source_id.

        Returns:
            List of announcement dicts.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fa.*, f.name as feature_name, fo.canonical_name, fo.status as option_status
            FROM feature_announcements fa
            LEFT JOIN features f ON fa.feature_id = f.feature_id
            LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
            WHERE fa.content_id = ?
            ORDER BY fa.section, fa.category, fa.h4_title
        """, (content_id,))

        rows = cursor.fetchall()
        announcements = []
        for row in rows:
            item = dict(row)
            if item.get("affected_areas"):
                try:
                    item["affected_areas"] = json.loads(item["affected_areas"])
                except json.JSONDecodeError:
                    item["affected_areas"] = []
            announcements.append(item)
        return announcements

    def announcement_exists(self, content_id: str, anchor_id: str) -> bool:
        """Check if an announcement already exists for this content and anchor.

        Args:
            content_id: The content item source_id.
            anchor_id: The H4 data-id anchor.

        Returns:
            True if announcement exists.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM feature_announcements WHERE content_id = ? AND anchor_id = ?",
            (content_id, anchor_id)
        )
        return cursor.fetchone() is not None

    # -------------------------------------------------------------------------
    # Upcoming Changes (from "Upcoming Canvas Changes" section)
    # -------------------------------------------------------------------------

    def insert_upcoming_change(
        self,
        content_id: str,
        change_date: str,
        description: str,
    ) -> int:
        """Insert an upcoming change.

        Args:
            content_id: FK to content_items.source_id.
            change_date: When the change will happen (ISO date).
            description: Description of the change.

        Returns:
            The ID of the inserted row.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO upcoming_changes (content_id, change_date, description)
            VALUES (?, ?, ?)
        """, (content_id, change_date, description))

        conn.commit()
        return cursor.lastrowid

    def get_upcoming_changes(self, days_ahead: int = 90) -> List[dict]:
        """Get upcoming changes within a date range.

        Args:
            days_ahead: Number of days to look ahead (default 90).

        Returns:
            List of upcoming change dicts, ordered by change_date.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_date = (datetime.now() + timedelta(days=days_ahead)).date().isoformat()

        cursor.execute("""
            SELECT uc.*, ci.title as release_note_title, ci.url as release_note_url
            FROM upcoming_changes uc
            JOIN content_items ci ON uc.content_id = ci.source_id
            WHERE uc.change_date <= ?
            ORDER BY uc.change_date ASC
        """, (cutoff_date,))

        return [dict(row) for row in cursor.fetchall()]

    def upcoming_change_exists(self, content_id: str, change_date: str, description: str) -> bool:
        """Check if an upcoming change already exists.

        Args:
            content_id: The content item source_id.
            change_date: The change date.
            description: The change description.

        Returns:
            True if change exists.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM upcoming_changes WHERE content_id = ? AND change_date = ? AND description = ?",
            (content_id, change_date, description)
        )
        return cursor.fetchone() is not None

    # -------------------------------------------------------------------------
    # Content Comments
    # -------------------------------------------------------------------------

    def insert_comment(
        self,
        content_id: str,
        comment_text: str,
        posted_at: Optional[datetime] = None,
        position: Optional[int] = None
    ) -> int:
        """Insert a comment for a content item.

        Args:
            content_id: The source_id of the content item.
            comment_text: The PII-redacted comment text.
            posted_at: When the comment was posted.
            position: Order in the thread (1, 2, 3...).

        Returns:
            The ID of the inserted comment row.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        posted_at_str = posted_at.isoformat() if isinstance(posted_at, datetime) else posted_at

        cursor.execute("""
            INSERT INTO content_comments (content_id, comment_text, posted_at, position)
            VALUES (?, ?, ?, ?)
        """, (content_id, comment_text, posted_at_str, position))

        conn.commit()
        return cursor.lastrowid

    def get_comments_for_content(
        self,
        content_id: str,
        limit: Optional[int] = None,
        order: str = 'asc'
    ) -> List[dict]:
        """Get comments for a content item.

        Args:
            content_id: The source_id of the content item.
            limit: Maximum number of comments to return.
            order: 'asc' for oldest first, 'desc' for newest first.

        Returns:
            List of comment dicts.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        order_clause = "DESC" if order == 'desc' else "ASC"
        limit_clause = f"LIMIT {limit}" if limit else ""

        cursor.execute(f"""
            SELECT id, content_id, comment_text, posted_at, position, created_at
            FROM content_comments
            WHERE content_id = ?
            ORDER BY posted_at {order_clause}
            {limit_clause}
        """, (content_id,))

        return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Feature Description Methods
    # -------------------------------------------------------------------------

    def update_feature_description(self, feature_id: str, description: str) -> None:
        """Update a feature's LLM-generated description."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE features
            SET description = ?, llm_generated_at = ?
            WHERE feature_id = ?
        """, (description, datetime.now().isoformat(), feature_id))
        conn.commit()

    def update_feature_option_description(self, option_id: str, description: str) -> None:
        """Update a feature option's LLM-generated description."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE feature_options
            SET description = ?, llm_generated_at = ?
            WHERE option_id = ?
        """, (description, datetime.now().isoformat(), option_id))
        conn.commit()

    def get_feature_option(self, option_id: str) -> Optional[dict]:
        """Get a feature option by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feature_options WHERE option_id = ?", (option_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_features_missing_description(self) -> List[dict]:
        """Get all features that don't have LLM descriptions yet."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM features
            WHERE description IS NULL OR description = ''
            ORDER BY name
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_feature_options_missing_description(self) -> List[dict]:
        """Get all feature options that don't have LLM descriptions yet."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM feature_options
            WHERE description IS NULL OR description = ''
            ORDER BY name
        """)
        return [dict(row) for row in cursor.fetchall()]

    def update_feature_option_meta_summary(self, option_id: str, meta_summary: str) -> None:
        """Update a feature option's meta_summary.

        Args:
            option_id: The option ID.
            meta_summary: The LLM-generated meta_summary (3-4 sentences).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE feature_options
            SET meta_summary = ?, meta_summary_updated_at = ?
            WHERE option_id = ?
        """, (meta_summary, datetime.now().isoformat(), option_id))
        conn.commit()

    def get_latest_content_for_option(self, option_id: str, limit: int = 5) -> List[dict]:
        """Get the latest content items referencing a feature option.

        Used to generate meta_summary.

        Args:
            option_id: The feature option ID.
            limit: Maximum number of items to return.

        Returns:
            List of content item dicts with announcement data, newest first.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ci.*, fa.description as announcement_description, fa.implications
            FROM content_items ci
            JOIN content_feature_refs cfr ON ci.source_id = cfr.content_id
            LEFT JOIN feature_announcements fa ON ci.source_id = fa.content_id
            WHERE cfr.feature_option_id = ?
            ORDER BY ci.first_posted DESC
            LIMIT ?
        """, (option_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def update_feature_option_lifecycle_dates(
        self,
        option_id: str,
        beta_date: Optional[date] = None,
        production_date: Optional[date] = None,
        deprecation_date: Optional[date] = None
    ) -> None:
        """Update lifecycle dates for a feature option.

        Args:
            option_id: The option ID.
            beta_date: When available in beta.
            production_date: When available in production.
            deprecation_date: When deprecated.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build dynamic update based on provided dates
        updates = []
        values = []

        if beta_date is not None:
            updates.append("beta_date = ?")
            values.append(beta_date.isoformat() if hasattr(beta_date, 'isoformat') else beta_date)
        if production_date is not None:
            updates.append("production_date = ?")
            values.append(production_date.isoformat() if hasattr(production_date, 'isoformat') else production_date)
        if deprecation_date is not None:
            updates.append("deprecation_date = ?")
            values.append(deprecation_date.isoformat() if hasattr(deprecation_date, 'isoformat') else deprecation_date)

        if updates:
            values.append(option_id)
            cursor.execute(f"""
                UPDATE feature_options
                SET {', '.join(updates)}
                WHERE option_id = ?
            """, values)
            conn.commit()

    def update_feature_option_implementation_status(self, option_id: str, status: str) -> None:
        """Update the template-generated implementation_status.

        Args:
            option_id: The option ID.
            status: The generated implementation status text.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE feature_options
            SET implementation_status = ?
            WHERE option_id = ?
        """, (status, option_id))
        conn.commit()

    def get_content_by_feature(self, feature_id: str) -> List[dict]:
        """Get all content items linked to a specific feature.

        Args:
            feature_id: The feature ID to search for.

        Returns:
            List of content item dicts.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ci.*
            FROM content_items ci
            JOIN content_feature_refs cfr ON ci.source_id = cfr.content_id
            WHERE cfr.feature_id = ?
            ORDER BY ci.first_posted DESC
        """, (feature_id,))
        return [dict(row) for row in cursor.fetchall()]

    def reassign_content_feature(self, old_feature_id: str, content_id: str, new_feature_id: str) -> None:
        """Reassign content from one feature to another.

        Args:
            old_feature_id: Current feature ID.
            content_id: The content source_id.
            new_feature_id: New feature to assign to.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE content_feature_refs
            SET feature_id = ?
            WHERE content_id = ? AND feature_id = ?
        """, (new_feature_id, content_id, old_feature_id))
        conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
