# Canvas-RSS Implementation Plan - Stage 1: Database Schema

**Date:** 2026-02-03
**Project:** canvas-rss
**Stage:** 1 of 2 (Database Schema)
**Design Doc:** `docs/plans/2026-02-03-database-schema-redesign.md`

## Overview

Implement the new database schema to support feature-centric content tracking. This stage focuses on schema changes only - scraping changes will be Stage 2.

## Pre-requisites

- [x] Review and approve design doc: `docs/plans/2026-02-03-database-schema-redesign.md`

---

## Tasks

### Phase 1: Constants & Types

#### Task 1.1: Create constants module
**File:** `src/constants.py` (new file)

```python
"""Canonical constants for canvas-rss."""

CONTENT_TYPES = {
    'release_note',
    'deploy_note',
    'changelog',
    'blog',
    'question',
    'reddit',
    'status',
}

CANVAS_FEATURES = {
    # Core Course Features
    'announcements': 'Announcements',
    'assignments': 'Assignments',
    'discussions': 'Discussions',
    'files': 'Files',
    'modules': 'Modules',
    'pages': 'Pages',
    'classic_quizzes': 'Quizzes (Classic)',
    'new_quizzes': 'New Quizzes',
    'syllabus': 'Syllabus',

    # Grading & Assessment
    'gradebook': 'Gradebook',
    'speedgrader': 'SpeedGrader',
    'rubrics': 'Rubrics',
    'outcomes': 'Outcomes',
    'mastery_paths': 'Mastery Paths',
    'peer_reviews': 'Peer Reviews',

    # Collaboration
    'collaborations': 'Collaborations',
    'conferences': 'Conferences',
    'groups': 'Groups',
    'chat': 'Chat',

    # Communication
    'inbox': 'Inbox',
    'calendar': 'Calendar',
    'notifications': 'Notifications',

    # User Interface
    'dashboard': 'Dashboard',
    'global_navigation': 'Global Navigation',
    'profile_settings': 'Profile and User Settings',
    'rich_content_editor': 'Rich Content Editor (RCE)',

    # Portfolio & Showcase
    'eportfolios': 'ePortfolios',
    'student_eportfolios': 'Canvas Student ePortfolios',

    # Analytics & Data
    'canvas_analytics': 'Canvas Analytics',
    'canvas_data_services': 'Canvas Data Services',

    # Add-on Products
    'canvas_catalog': 'Canvas Catalog',
    'canvas_studio': 'Canvas Studio',
    'canvas_commons': 'Canvas Commons',
    'student_pathways': 'Canvas Student Pathways',
    'mastery_connect': 'Mastery Connect',
    'parchment_badges': 'Parchment Digital Badges',

    # Mobile
    'canvas_mobile': 'Canvas Mobile',

    # Administration
    'course_import': 'Course Import Tool',
    'blueprint_courses': 'Blueprint Courses',
    'sis_import': 'SIS Import',
    'external_apps_lti': 'External Apps (LTI)',
    'api': 'Web Services / API',
    'account_settings': 'Account Settings',
    'themes_branding': 'Themes/Branding',
    'authentication': 'Authentication',

    # Specialized
    'canvas_elementary': 'Canvas for Elementary',

    # Catch-all
    'general': 'General',
}

FEATURE_OPTION_STATUSES = {
    'pending',          # Announced but not yet available
    'preview',          # Feature preview / beta
    'optional',         # Available but disabled by default
    'default_optional', # Enabled by default, can be disabled
    'released',         # Fully released, no longer a feature option
}

MENTION_TYPES = {
    'announces',   # Content announces this feature/option
    'discusses',   # Content discusses/explains
    'questions',   # Content asks about
    'feedback',    # Content provides feedback/complaints
}
```

---

### Phase 2: Database Schema Changes

#### Task 2.1: Add new tables to schema
**File:** `src/utils/database.py`

Add to `_init_schema()`:

```python
# Features table (canonical Canvas features)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS features (
        feature_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Feature options table (sub-features with lifecycle)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS feature_options (
        option_id TEXT PRIMARY KEY,
        feature_id TEXT NOT NULL,
        name TEXT NOT NULL,
        summary TEXT,
        status TEXT NOT NULL,
        config_level TEXT,
        default_state TEXT,
        first_announced TIMESTAMP,
        last_updated TIMESTAMP,
        FOREIGN KEY (feature_id) REFERENCES features(feature_id)
    )
""")

# Content-feature junction table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS content_feature_refs (
        content_id TEXT NOT NULL,
        feature_id TEXT,
        feature_option_id TEXT,
        mention_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (content_id, COALESCE(feature_id, ''), COALESCE(feature_option_id, '')),
        FOREIGN KEY (feature_id) REFERENCES features(feature_id),
        FOREIGN KEY (feature_option_id) REFERENCES feature_options(option_id),
        CHECK (feature_id IS NOT NULL OR feature_option_id IS NOT NULL)
    )
""")

# Create indexes
cursor.execute("CREATE INDEX IF NOT EXISTS idx_feature_options_feature ON feature_options(feature_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_feature_options_status ON feature_options(status)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_feature_refs_feature ON content_feature_refs(feature_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_feature_refs_option ON content_feature_refs(feature_option_id)")
```

#### Task 2.2: Add new columns to content_items
**File:** `src/utils/database.py`

Add migrations for new columns:

```python
# Migration: Add source date columns
for col, col_type in [
    ('first_posted', 'TIMESTAMP'),
    ('last_edited', 'TIMESTAMP'),
    ('last_comment_at', 'TIMESTAMP'),
    ('last_checked_at', 'TIMESTAMP'),
]:
    try:
        cursor.execute(f"ALTER TABLE content_items ADD COLUMN {col} {col_type}")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

# Migration: Add content_id as alias for source_id (for new code)
# Note: SQLite doesn't support RENAME COLUMN in older versions
# We'll use source_id internally but expose as content_id in new methods
```

#### Task 2.3: Seed features table
**File:** `src/utils/database.py`

Add method to seed canonical features:

```python
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
            logger.warning(f"Failed to seed feature {feature_id}: {e}")

    conn.commit()
    return inserted
```

---

### Phase 3: New Database Methods

#### Task 3.1: Feature CRUD methods
**File:** `src/utils/database.py`

```python
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
```

#### Task 3.2: Feature option CRUD methods
**File:** `src/utils/database.py`

```python
def upsert_feature_option(
    self,
    option_id: str,
    feature_id: str,
    name: str,
    status: str,
    summary: str = None,
    config_level: str = None,
    default_state: str = None,
    first_announced: str = None,
) -> None:
    """Insert or update a feature option."""
    conn = self._get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO feature_options
            (option_id, feature_id, name, summary, status, config_level, default_state, first_announced, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(option_id) DO UPDATE SET
            name = excluded.name,
            summary = excluded.summary,
            status = excluded.status,
            config_level = excluded.config_level,
            default_state = excluded.default_state,
            last_updated = ?
    """, (option_id, feature_id, name, summary, status, config_level, default_state, first_announced, now, now))
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
```

#### Task 3.3: Content-feature reference methods
**File:** `src/utils/database.py`

```python
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
```

---

### Phase 4: Update ContentItem Dataclass

#### Task 4.1: Update ContentItem fields
**File:** `src/processor/content_processor.py`

Update the dataclass to include new date fields:

```python
@dataclass
class ContentItem:
    """A processed content item ready for storage."""

    # Identity (renamed for clarity, source_id still used internally)
    source: str  # Keep for backwards compat, derived from content_type
    source_id: str  # Will migrate to content_id
    content_type: str

    # Content
    title: str
    url: str
    summary: str = ""

    # Source dates
    first_posted: Optional[datetime] = None
    last_edited: Optional[datetime] = None
    last_comment_at: Optional[datetime] = None
    comment_count: int = 0

    # Engagement
    engagement_score: int = 0

    # Deprecated fields (keep for backwards compat during migration)
    content: str = ""
    published_date: Any = None  # Use first_posted instead
    sentiment: str = ""
    primary_topic: str = ""
    topics: List[str] = None

    # RSS-only fields (not stored in DB)
    is_latest: bool = False
    has_tracking_badge: bool = False
    structured_description: str = ""
    is_new_post: bool = False
    previous_comment_count: int = 0
    new_comment_count: int = 0
    latest_comment_preview: str = ""
```

---

### Phase 5: Testing

#### Task 5.1: Unit tests for new tables
**File:** `tests/test_database.py`

- Test features table CRUD
- Test feature_options table CRUD
- Test content_feature_refs junction
- Test seed_features()
- Test queries across junction

#### Task 5.2: Migration test
**File:** `tests/test_database.py`

- Test that migrations run on existing database without error
- Test that new columns are added correctly
- Test backwards compatibility with existing data

---

## Verification Checklist

Before marking complete:

- [ ] Constants module created with CONTENT_TYPES, CANVAS_FEATURES, etc.
- [ ] New tables created (features, feature_options, content_feature_refs)
- [ ] New columns added to content_items
- [ ] Features table seeded with canonical features
- [ ] All new CRUD methods implemented
- [ ] ContentItem dataclass updated
- [ ] All tests pass
- [ ] Existing functionality still works (RSS feed generation)

---

## What's NOT in Stage 1

The following will be addressed in Stage 2 (Scraping Changes):

- Extracting source dates (first_posted, last_edited, last_comment_at) from DOM
- Fixing content_id generation to use actual IDs
- Feature/feature_option classification logic
- LLM-based feature matching for community posts

---

## Notes

- Keep `source_id` column name in DB for now (avoid complex migration)
- Expose as `content_id` in new method signatures
- Deprecated columns remain in schema but stop being populated
- RSS feed generation should continue to work unchanged
