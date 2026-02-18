# LLM Summarization Redesign - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement database-first LLM summarization with structured fields (description, implications, meta_summary) for website display.

**Architecture:** Clean v2.0 database schema with unified feature_announcements for all content types. LLM processing during scrape only, never at query time. Template-based implementation_status. CLI for regeneration and triage.

**Tech Stack:** Python 3.11+, SQLite, Google Gemini API, argparse (CLI), pytest

---

## Phase 1: Database Schema Updates

### Task 1.1: Add columns to features table

**Files:**
- Modify: `src/utils/database.py:105-113`
- Test: `tests/test_database.py`

**Step 1: Write the failing test**

Add to `tests/test_database.py`:

```python
class TestFeaturesTableV2:
    """Tests for v2.0 features table columns."""

    def test_features_table_has_description_column(self, temp_db):
        """Test that features table has description column."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(features)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'description' in columns

    def test_features_table_has_llm_generated_at_column(self, temp_db):
        """Test that features table has llm_generated_at column."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(features)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'llm_generated_at' in columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestFeaturesTableV2 -v`
Expected: FAIL - columns don't exist

**Step 3: Update schema in database.py**

In `src/utils/database.py`, update the features table creation (around line 106):

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestFeaturesTableV2 -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add description and llm_generated_at to features table"
```

---

### Task 1.2: Add columns to feature_options table

**Files:**
- Modify: `src/utils/database.py:116-133`
- Test: `tests/test_database.py`

**Step 1: Write the failing test**

```python
class TestFeatureOptionsTableV2:
    """Tests for v2.0 feature_options table columns."""

    def test_feature_options_has_description_column(self, temp_db):
        """Test that feature_options has description column."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feature_options)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'description' in columns

    def test_feature_options_has_meta_summary_column(self, temp_db):
        """Test that feature_options has meta_summary column."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feature_options)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'meta_summary' in columns

    def test_feature_options_has_meta_summary_updated_at_column(self, temp_db):
        """Test that feature_options has meta_summary_updated_at column."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feature_options)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'meta_summary_updated_at' in columns

    def test_feature_options_has_implementation_status_column(self, temp_db):
        """Test that feature_options has implementation_status column."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feature_options)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'implementation_status' in columns

    def test_feature_options_has_lifecycle_date_columns(self, temp_db):
        """Test that feature_options has beta_date, production_date, deprecation_date."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feature_options)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'beta_date' in columns
        assert 'production_date' in columns
        assert 'deprecation_date' in columns

    def test_feature_options_has_llm_generated_at_column(self, temp_db):
        """Test that feature_options has llm_generated_at column."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feature_options)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'llm_generated_at' in columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestFeatureOptionsTableV2 -v`
Expected: FAIL

**Step 3: Update schema**

In `src/utils/database.py`, update feature_options table:

```python
# Feature options table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS feature_options (
        option_id TEXT PRIMARY KEY,
        feature_id TEXT NOT NULL,
        name TEXT NOT NULL,
        canonical_name TEXT,
        description TEXT,
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestFeatureOptionsTableV2 -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add v2.0 columns to feature_options (description, meta_summary, lifecycle dates)"
```

---

### Task 1.3: Update feature_announcements table

**Files:**
- Modify: `src/utils/database.py:169-205`
- Test: `tests/test_database.py`

**Step 1: Write the failing test**

```python
class TestFeatureAnnouncementsTableV2:
    """Tests for v2.0 feature_announcements table columns."""

    def test_feature_announcements_has_description_column(self, temp_db):
        """Test that feature_announcements has description column (replaces summary)."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feature_announcements)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'description' in columns

    def test_feature_announcements_has_implications_column(self, temp_db):
        """Test that feature_announcements has implications column."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feature_announcements)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'implications' in columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestFeatureAnnouncementsTableV2 -v`
Expected: FAIL

**Step 3: Update schema**

In `src/utils/database.py`, update feature_announcements table:

```python
# Feature announcements table (each H4 entry from release/deploy notes, or blog/Q&A posts)
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

        FOREIGN KEY (feature_id) REFERENCES features(feature_id),
        FOREIGN KEY (option_id) REFERENCES feature_options(option_id),
        FOREIGN KEY (content_id) REFERENCES content_items(source_id)
    )
""")

# Migration: Add description and implications columns
for col in ['description', 'implications']:
    try:
        cursor.execute(f"ALTER TABLE feature_announcements ADD COLUMN {col} TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestFeatureAnnouncementsTableV2 -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add description and implications to feature_announcements"
```

---

### Task 1.4: Create content_comments table

**Files:**
- Modify: `src/utils/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing test**

```python
class TestContentCommentsTable:
    """Tests for content_comments table."""

    def test_content_comments_table_exists(self, temp_db):
        """Test that content_comments table exists."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='content_comments'"
        )
        assert cursor.fetchone() is not None

    def test_content_comments_has_required_columns(self, temp_db):
        """Test that content_comments has all required columns."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(content_comments)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'id' in columns
        assert 'content_id' in columns
        assert 'comment_text' in columns
        assert 'posted_at' in columns
        assert 'position' in columns
        assert 'created_at' in columns

    def test_content_comments_has_no_author_column(self, temp_db):
        """Test that content_comments does NOT have author column (anonymity)."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(content_comments)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'author' not in columns
        assert 'user' not in columns
        assert 'username' not in columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestContentCommentsTable -v`
Expected: FAIL

**Step 3: Add table creation in _init_schema()**

In `src/utils/database.py`, add after upcoming_changes table:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestContentCommentsTable -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add content_comments table for blog/Q&A comments (anonymous)"
```

---

### Task 1.5: Add database methods for comments

**Files:**
- Modify: `src/utils/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing tests**

```python
class TestContentCommentsMethods:
    """Tests for content_comments database methods."""

    def test_insert_comment(self, temp_db, sample_content_item):
        """Test inserting a comment."""
        temp_db.insert_item(sample_content_item)
        comment_id = temp_db.insert_comment(
            content_id=sample_content_item.source_id,
            comment_text="This is a test comment",
            posted_at=datetime.now(),
            position=1
        )
        assert comment_id > 0

    def test_get_comments_for_content(self, temp_db, sample_content_item):
        """Test retrieving comments for a content item."""
        temp_db.insert_item(sample_content_item)
        temp_db.insert_comment(sample_content_item.source_id, "First comment", datetime.now(), 1)
        temp_db.insert_comment(sample_content_item.source_id, "Second comment", datetime.now(), 2)

        comments = temp_db.get_comments_for_content(sample_content_item.source_id)
        assert len(comments) == 2
        assert comments[0]['position'] == 1
        assert comments[1]['position'] == 2

    def test_get_comments_ordered_by_posted_at_desc(self, temp_db, sample_content_item):
        """Test that comments are returned newest first."""
        temp_db.insert_item(sample_content_item)
        older = datetime.now() - timedelta(hours=2)
        newer = datetime.now()
        temp_db.insert_comment(sample_content_item.source_id, "Older", older, 1)
        temp_db.insert_comment(sample_content_item.source_id, "Newer", newer, 2)

        comments = temp_db.get_comments_for_content(sample_content_item.source_id, order='desc')
        assert comments[0]['comment_text'] == "Newer"

    def test_get_latest_comments_with_limit(self, temp_db, sample_content_item):
        """Test retrieving limited number of recent comments."""
        temp_db.insert_item(sample_content_item)
        for i in range(10):
            temp_db.insert_comment(sample_content_item.source_id, f"Comment {i}", datetime.now(), i)

        comments = temp_db.get_comments_for_content(sample_content_item.source_id, limit=5)
        assert len(comments) == 5
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestContentCommentsMethods -v`
Expected: FAIL - methods don't exist

**Step 3: Implement methods**

In `src/utils/database.py`, add:

```python
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
        List of comment dicts with keys: id, content_id, comment_text, posted_at, position.
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestContentCommentsMethods -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add insert_comment and get_comments_for_content methods"
```

---

### Task 1.6: Add database methods for feature description updates

**Files:**
- Modify: `src/utils/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing tests**

```python
class TestFeatureDescriptionMethods:
    """Tests for feature description update methods."""

    def test_update_feature_description(self, temp_db):
        """Test updating a feature's description."""
        from src.constants import CANVAS_FEATURES
        temp_db.seed_features()

        temp_db.update_feature_description('speedgrader', 'SpeedGrader is an inline grading tool.')

        feature = temp_db.get_feature('speedgrader')
        assert feature['description'] == 'SpeedGrader is an inline grading tool.'
        assert feature['llm_generated_at'] is not None

    def test_update_feature_option_description(self, temp_db):
        """Test updating a feature option's description."""
        temp_db.seed_features()
        temp_db.upsert_feature_option(
            option_id='test_option',
            feature_id='speedgrader',
            name='Test Option',
            status='preview'
        )

        temp_db.update_feature_option_description('test_option', 'This option enables testing.')

        option = temp_db.get_feature_option('test_option')
        assert option['description'] == 'This option enables testing.'
        assert option['llm_generated_at'] is not None

    def test_get_features_missing_description(self, temp_db):
        """Test getting features that don't have descriptions."""
        temp_db.seed_features()
        temp_db.update_feature_description('speedgrader', 'Has description')

        missing = temp_db.get_features_missing_description()
        assert 'speedgrader' not in [f['feature_id'] for f in missing]
        assert len(missing) > 0  # Other features should be missing
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestFeatureDescriptionMethods -v`
Expected: FAIL

**Step 3: Implement methods**

In `src/utils/database.py`, add:

```python
def update_feature_description(self, feature_id: str, description: str) -> None:
    """Update a feature's LLM-generated description.

    Args:
        feature_id: The feature ID.
        description: The LLM-generated description (1-2 sentences).
    """
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE features
        SET description = ?, llm_generated_at = ?
        WHERE feature_id = ?
    """, (description, datetime.now().isoformat(), feature_id))
    conn.commit()

def update_feature_option_description(self, option_id: str, description: str) -> None:
    """Update a feature option's LLM-generated description.

    Args:
        option_id: The option ID.
        description: The LLM-generated description (1-2 sentences).
    """
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE feature_options
        SET description = ?, llm_generated_at = ?
        WHERE option_id = ?
    """, (description, datetime.now().isoformat(), option_id))
    conn.commit()

def get_feature_option(self, option_id: str) -> Optional[dict]:
    """Get a feature option by ID.

    Args:
        option_id: The option ID.

    Returns:
        Dict with option data, or None if not found.
    """
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feature_options WHERE option_id = ?", (option_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

def get_features_missing_description(self) -> List[dict]:
    """Get all features that don't have LLM descriptions yet.

    Returns:
        List of feature dicts without descriptions.
    """
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM features
        WHERE description IS NULL OR description = ''
        ORDER BY name
    """)
    return [dict(row) for row in cursor.fetchall()]

def get_feature_options_missing_description(self) -> List[dict]:
    """Get all feature options that don't have LLM descriptions yet.

    Returns:
        List of feature option dicts without descriptions.
    """
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM feature_options
        WHERE description IS NULL OR description = ''
        ORDER BY name
    """)
    return [dict(row) for row in cursor.fetchall()]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestFeatureDescriptionMethods -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add methods for updating feature/option descriptions"
```

---

### Task 1.7: Add database methods for meta_summary

**Files:**
- Modify: `src/utils/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing tests**

```python
class TestMetaSummaryMethods:
    """Tests for meta_summary database methods."""

    def test_update_feature_option_meta_summary(self, temp_db):
        """Test updating meta_summary for a feature option."""
        temp_db.seed_features()
        temp_db.upsert_feature_option('test_opt', 'speedgrader', 'Test', status='preview')

        temp_db.update_feature_option_meta_summary('test_opt', 'Ready for deployment. Positive feedback.')

        option = temp_db.get_feature_option('test_opt')
        assert option['meta_summary'] == 'Ready for deployment. Positive feedback.'
        assert option['meta_summary_updated_at'] is not None

    def test_get_latest_content_for_option(self, temp_db, sample_content_item):
        """Test getting latest content items for meta_summary generation."""
        temp_db.seed_features()
        temp_db.upsert_feature_option('test_opt', 'speedgrader', 'Test', status='preview')
        temp_db.insert_item(sample_content_item)
        temp_db.add_content_feature_ref(
            content_id=sample_content_item.source_id,
            feature_option_id='test_opt',
            mention_type='announces'
        )

        content = temp_db.get_latest_content_for_option('test_opt', limit=5)
        assert len(content) == 1
        assert content[0]['source_id'] == sample_content_item.source_id
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestMetaSummaryMethods -v`
Expected: FAIL

**Step 3: Implement methods**

In `src/utils/database.py`, add:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestMetaSummaryMethods -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add meta_summary update and content retrieval methods"
```

---

### Task 1.8: Add database methods for lifecycle dates

**Files:**
- Modify: `src/utils/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing tests**

```python
class TestLifecycleDateMethods:
    """Tests for feature option lifecycle date methods."""

    def test_update_feature_option_lifecycle_dates(self, temp_db):
        """Test updating beta_date and production_date."""
        from datetime import date
        temp_db.seed_features()
        temp_db.upsert_feature_option('test_opt', 'speedgrader', 'Test', status='preview')

        temp_db.update_feature_option_lifecycle_dates(
            option_id='test_opt',
            beta_date=date(2026, 1, 19),
            production_date=date(2026, 2, 21)
        )

        option = temp_db.get_feature_option('test_opt')
        assert option['beta_date'] == '2026-01-19'
        assert option['production_date'] == '2026-02-21'

    def test_update_implementation_status(self, temp_db):
        """Test updating implementation_status."""
        temp_db.seed_features()
        temp_db.upsert_feature_option('test_opt', 'speedgrader', 'Test', status='preview')

        temp_db.update_feature_option_implementation_status(
            'test_opt',
            'In feature preview (beta). Account-level setting. Beta: Jan 19, 2026.'
        )

        option = temp_db.get_feature_option('test_opt')
        assert 'feature preview' in option['implementation_status']
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestLifecycleDateMethods -v`
Expected: FAIL

**Step 3: Implement methods**

In `src/utils/database.py`, add:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestLifecycleDateMethods -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add lifecycle date and implementation_status update methods"
```

---

## Phase 2: Content Processor Updates

### Task 2.1: Add implementation_status template generator

**Files:**
- Modify: `src/processor/content_processor.py`
- Test: `tests/test_processor.py`

**Step 1: Write the failing test**

Add to `tests/test_processor.py`:

```python
class TestImplementationStatusGenerator:
    """Tests for implementation_status template generation."""

    def test_generate_implementation_status_preview(self):
        """Test generating status for preview option."""
        from processor.content_processor import generate_implementation_status
        from datetime import date

        status = generate_implementation_status(
            status='preview',
            config_level='account',
            beta_date=date(2026, 1, 19),
            production_date=date(2026, 2, 21),
            first_announced=date(2026, 1, 1)
        )

        assert 'feature preview' in status.lower()
        assert 'Account' in status
        assert 'Jan 19, 2026' in status or 'Beta' in status

    def test_generate_implementation_status_released(self):
        """Test generating status for released option."""
        from processor.content_processor import generate_implementation_status
        from datetime import date

        status = generate_implementation_status(
            status='released',
            production_date=date(2025, 6, 1)
        )

        assert 'released' in status.lower() or 'production' in status.lower()

    def test_generate_implementation_status_future_dates(self):
        """Test that future dates are shown with specific dates."""
        from processor.content_processor import generate_implementation_status
        from datetime import date, timedelta

        future = date.today() + timedelta(days=30)
        status = generate_implementation_status(
            status='preview',
            production_date=future
        )

        assert 'Production:' in status or future.strftime('%b') in status
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_processor.py::TestImplementationStatusGenerator -v`
Expected: FAIL

**Step 3: Implement function**

In `src/processor/content_processor.py`, add:

```python
from datetime import date as date_type

def generate_implementation_status(
    status: str,
    config_level: Optional[str] = None,
    default_state: Optional[str] = None,
    beta_date: Optional[date_type] = None,
    production_date: Optional[date_type] = None,
    deprecation_date: Optional[date_type] = None,
    first_announced: Optional[date_type] = None
) -> str:
    """Generate implementation_status from structured data (no LLM).

    Args:
        status: Feature option status ('pending', 'preview', 'optional', 'default_on', 'released').
        config_level: 'account', 'course', or 'both'.
        default_state: 'enabled' or 'disabled'.
        beta_date: When available in beta.
        production_date: When available in production.
        deprecation_date: When deprecated.
        first_announced: When first announced.

    Returns:
        Human-readable implementation status string.
    """
    status_map = {
        'pending': 'Not yet available',
        'preview': 'In feature preview (beta)',
        'optional': 'Available, disabled by default',
        'default_on': 'Available, enabled by default',
        'released': 'Fully released'
    }

    parts = [status_map.get(status, status)]

    if config_level:
        parts.append(f"{config_level.title()}-level setting")

    today = date_type.today()

    if beta_date:
        if beta_date > today:
            parts.append(f"Beta: {beta_date.strftime('%b %d, %Y')}")
        else:
            parts.append(f"In beta since {beta_date.strftime('%b %Y')}")

    if production_date:
        if production_date > today:
            parts.append(f"Production: {production_date.strftime('%b %d, %Y')}")
        else:
            parts.append(f"In production since {production_date.strftime('%b %Y')}")

    if deprecation_date:
        if deprecation_date > today:
            parts.append(f"Deprecation: {deprecation_date.strftime('%b %d, %Y')}")
        else:
            parts.append(f"Deprecated {deprecation_date.strftime('%b %Y')}")

    if first_announced and not any([beta_date, production_date]):
        parts.append(f"First announced {first_announced.strftime('%b %Y')}")

    return ". ".join(parts) + "."
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_processor.py::TestImplementationStatusGenerator -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/processor/content_processor.py tests/test_processor.py
git commit -m "feat(processor): add generate_implementation_status template function"
```

---

### Task 2.2: Add new LLM prompts

**Files:**
- Modify: `src/processor/content_processor.py`
- Test: `tests/test_processor.py`

**Step 1: Write the failing test**

```python
class TestV2Prompts:
    """Tests for v2.0 LLM prompt methods."""

    def test_summarize_feature_description_returns_string(self, mock_processor):
        """Test that summarize_feature_description returns a string."""
        result = mock_processor.summarize_feature_description(
            feature_name='SpeedGrader',
            content_snippet='SpeedGrader allows inline grading...'
        )
        assert isinstance(result, str)

    def test_summarize_feature_option_description_returns_string(self, mock_processor):
        """Test that summarize_feature_option_description returns a string."""
        result = mock_processor.summarize_feature_option_description(
            option_name='Performance Upgrades',
            feature_name='SpeedGrader',
            raw_content='This feature improves...'
        )
        assert isinstance(result, str)

    def test_summarize_announcement_description_returns_string(self, mock_processor):
        """Test that summarize_announcement_description returns a string."""
        result = mock_processor.summarize_announcement_description(
            h4_title='Document Processing',
            raw_content='New document processing capabilities...'
        )
        assert isinstance(result, str)

    def test_summarize_announcement_implications_returns_string(self, mock_processor):
        """Test that summarize_announcement_implications returns a string."""
        result = mock_processor.summarize_announcement_implications(
            h4_title='Document Processing',
            raw_content='New document processing capabilities...',
            feature_name='Files'
        )
        assert isinstance(result, str)

    def test_generate_meta_summary_returns_string(self, mock_processor):
        """Test that generate_meta_summary returns a string."""
        result = mock_processor.generate_meta_summary(
            option_name='Performance Upgrades',
            feature_name='SpeedGrader',
            implementation_status='In production since Feb 2026.',
            content_summaries=[
                {'date': '2026-02-21', 'title': 'Released', 'description': 'Now live', 'implications': 'Ready to use'},
            ]
        )
        assert isinstance(result, str)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_processor.py::TestV2Prompts -v`
Expected: FAIL

**Step 3: Implement methods**

In `src/processor/content_processor.py`, add to `ContentProcessor` class:

```python
def summarize_feature_description(self, feature_name: str, content_snippet: str) -> str:
    """Generate a 1-2 sentence description for a feature.

    Args:
        feature_name: Name of the Canvas feature.
        content_snippet: Recent content about the feature.

    Returns:
        1-2 sentence description.
    """
    if not self.client:
        return ""

    prompt = f"""You are summarizing Canvas LMS features for educational technologists.

Describe what {feature_name} is in 1-2 sentences. Be concise and factual.

Context from recent content:
{content_snippet[:2000]}"""

    return self._call_llm(prompt, max_chars=300)

def summarize_feature_option_description(
    self, option_name: str, feature_name: str, raw_content: str
) -> str:
    """Generate a 1-2 sentence description for a feature option.

    Args:
        option_name: Name of the feature option.
        feature_name: Name of the parent feature.
        raw_content: Raw content from announcement.

    Returns:
        1-2 sentence description.
    """
    if not self.client:
        return ""

    prompt = f"""You are summarizing a Canvas LMS feature option for educational technologists.

Feature option: {option_name}
Parent feature: {feature_name}

Describe what this feature option does in 1-2 sentences. Be concise and factual.

Context:
{raw_content[:2000]}"""

    return self._call_llm(prompt, max_chars=300)

def summarize_announcement_description(self, h4_title: str, raw_content: str) -> str:
    """Generate a 1-2 sentence description for a feature announcement.

    Args:
        h4_title: The H4 title from release notes.
        raw_content: The raw content after the H4.

    Returns:
        1-2 sentence description.
    """
    if not self.client:
        return ""

    prompt = f"""Summarize this Canvas release note entry in 1-2 sentences. What changed or was added?

Title: {h4_title}
Content: {raw_content[:2000]}"""

    return self._call_llm(prompt, max_chars=300)

def summarize_announcement_implications(
    self, h4_title: str, raw_content: str, feature_name: str
) -> str:
    """Generate 2-3 sentence implications for a feature announcement.

    Args:
        h4_title: The H4 title from release notes.
        raw_content: The raw content after the H4.
        feature_name: Name of the related feature.

    Returns:
        2-3 sentence implications for ed techs.
    """
    if not self.client:
        return ""

    prompt = f"""In 2-3 sentences, explain who is affected by this change and what educational technologists should know. Be actionable.

Title: {h4_title}
Content: {raw_content[:2000]}
Feature: {feature_name}"""

    return self._call_llm(prompt, max_chars=500)

def summarize_announcement_implications_from_comments(
    self, title: str, initial_content: str, comments: List[dict]
) -> str:
    """Generate implications from blog/Q&A comments.

    Args:
        title: The post title.
        initial_content: The initial post content.
        comments: List of comment dicts with 'comment_text' and 'posted_at'.

    Returns:
        2-3 sentence implications based on discussion.
    """
    if not self.client:
        return ""

    # Format comments, newest first
    comments_text = "\n".join([
        f"- {c.get('comment_text', '')[:500]}"
        for c in sorted(comments, key=lambda x: x.get('posted_at', ''), reverse=True)[:10]
    ])

    prompt = f"""In 2-3 sentences, summarize the community discussion and what educational technologists should know. Weight recent comments more heavily. Be actionable.

Title: {title}
Initial post: {initial_content[:1000]}

Comments (newest first):
{comments_text}"""

    return self._call_llm(prompt, max_chars=500)

def generate_meta_summary(
    self,
    option_name: str,
    feature_name: str,
    implementation_status: str,
    content_summaries: List[dict]
) -> str:
    """Generate meta_summary for a feature option from latest content.

    Args:
        option_name: Name of the feature option.
        feature_name: Name of the parent feature.
        implementation_status: Current implementation status text.
        content_summaries: List of dicts with 'date', 'title', 'description', 'implications'.

    Returns:
        3-4 sentence meta summary.
    """
    if not self.client:
        return ""

    # Format content summaries
    summaries_text = "\n".join([
        f"- [{c.get('date', 'Unknown')}] {c.get('title', '')}: {c.get('description', '')} {c.get('implications', '')}"
        for c in content_summaries[:5]
    ])

    prompt = f"""You are advising educational technologists about the deployment readiness of a Canvas feature option.

Feature option: {option_name}
Parent feature: {feature_name}
Current status: {implementation_status}

Recent activity (newest first):
{summaries_text}

In 3-4 sentences, summarize the current state of this feature option for ed techs considering deployment. Cover: readiness for wide rollout, recent changes (especially status transitions like beta→production), community sentiment, and any concerns. Be direct and actionable."""

    return self._call_llm(prompt, max_chars=600)

def _call_llm(self, prompt: str, max_chars: int = 500) -> str:
    """Internal method to call LLM with retry logic.

    Args:
        prompt: The prompt to send.
        max_chars: Maximum characters in response.

    Returns:
        LLM response text, truncated if needed.
    """
    try:
        response = self._call_with_retry(
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.generation_config
            ),
            fallback=""
        )

        if response and hasattr(response, 'text'):
            text = response.text.strip()
            # Truncate at word boundary
            if len(text) > max_chars:
                text = text[:max_chars].rsplit(' ', 1)[0] + '...'
            return text
        return ""
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return ""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_processor.py::TestV2Prompts -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/processor/content_processor.py tests/test_processor.py
git commit -m "feat(processor): add v2.0 LLM summarization methods"
```

---

## Phase 3: CLI Implementation

### Task 3.1: Create CLI module structure

**Files:**
- Create: `src/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
"""Tests for CLI module."""

import pytest
from unittest.mock import MagicMock, patch


class TestCLIStructure:
    """Tests for CLI module structure."""

    def test_cli_module_exists(self):
        """Test that cli module can be imported."""
        from src import cli
        assert cli is not None

    def test_cli_has_main_function(self):
        """Test that cli has main() function."""
        from src.cli import main
        assert callable(main)

    def test_cli_has_regenerate_command(self):
        """Test that regenerate command is registered."""
        from src.cli import create_parser
        parser = create_parser()
        # Should not raise
        args = parser.parse_args(['regenerate', 'feature', 'speedgrader'])
        assert args.command == 'regenerate'

    def test_cli_has_general_command(self):
        """Test that general command is registered."""
        from src.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(['general', 'list'])
        assert args.command == 'general'
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py::TestCLIStructure -v`
Expected: FAIL - module doesn't exist

**Step 3: Create CLI module**

Create `src/cli.py`:

```python
"""Command-line interface for canvas-rss management."""

import argparse
import sys
from typing import Optional


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog='canvas-rss',
        description='Canvas RSS Aggregator CLI'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Regenerate command
    regen_parser = subparsers.add_parser('regenerate', help='Regenerate LLM summaries')
    regen_subparsers = regen_parser.add_subparsers(dest='regen_type', help='What to regenerate')

    # regenerate feature <id>
    regen_feature = regen_subparsers.add_parser('feature', help='Regenerate feature description')
    regen_feature.add_argument('feature_id', help='Feature ID to regenerate')

    # regenerate option <id>
    regen_option = regen_subparsers.add_parser('option', help='Regenerate option description')
    regen_option.add_argument('option_id', help='Option ID to regenerate')

    # regenerate meta-summary <id>
    regen_meta = regen_subparsers.add_parser('meta-summary', help='Regenerate meta summary')
    regen_meta.add_argument('option_id', help='Option ID to regenerate')

    # regenerate features --missing
    regen_features = regen_subparsers.add_parser('features', help='Regenerate all features')
    regen_features.add_argument('--missing', action='store_true', help='Only missing descriptions')
    regen_features.add_argument('--dry-run', action='store_true', help='Show what would be done')

    # regenerate options --missing
    regen_options = regen_subparsers.add_parser('options', help='Regenerate all options')
    regen_options.add_argument('--missing', action='store_true', help='Only missing descriptions')
    regen_options.add_argument('--dry-run', action='store_true', help='Show what would be done')

    # regenerate meta-summaries --all
    regen_metas = regen_subparsers.add_parser('meta-summaries', help='Regenerate all meta summaries')
    regen_metas.add_argument('--all', action='store_true', help='Regenerate all')
    regen_metas.add_argument('--dry-run', action='store_true', help='Show what would be done')

    # General command
    general_parser = subparsers.add_parser('general', help='Manage general-tagged content')
    general_subparsers = general_parser.add_subparsers(dest='general_action', help='Action')

    # general list
    general_subparsers.add_parser('list', help='List content tagged as general')

    # general show <id>
    general_show = general_subparsers.add_parser('show', help='Show details of an item')
    general_show.add_argument('content_id', help='Content ID to show')

    # general assign <id> --feature/--option/--new-feature/--new-option
    general_assign = general_subparsers.add_parser('assign', help='Assign to feature/option')
    general_assign.add_argument('content_id', help='Content ID to assign')
    general_assign.add_argument('--feature', help='Assign to existing feature')
    general_assign.add_argument('--option', help='Assign to existing option')
    general_assign.add_argument('--new-feature', nargs=2, metavar=('ID', 'NAME'), help='Create new feature')
    general_assign.add_argument('--new-option', nargs=3, metavar=('FEATURE_ID', 'OPTION_ID', 'NAME'), help='Create new option')

    # general triage
    general_triage = general_subparsers.add_parser('triage', help='Interactive triage')
    general_triage.add_argument('--auto-high', action='store_true', help='Auto-assign >80% confidence')
    general_triage.add_argument('--days', type=int, help='Only items from last N days')
    general_triage.add_argument('--export', metavar='FILE', help='Export suggestions to CSV')

    return parser


def main(args: Optional[list] = None) -> int:
    """Main entry point for CLI.

    Args:
        args: Command line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 for success).
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 1

    # Command handlers will be added in subsequent tasks
    print(f"Command: {parsed.command}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py::TestCLIStructure -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat(cli): create CLI module structure with regenerate and general commands"
```

---

### Task 3.2: Implement regenerate feature command

**Files:**
- Modify: `src/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

```python
class TestRegenerateFeature:
    """Tests for regenerate feature command."""

    @patch('src.cli.Database')
    @patch('src.cli.ContentProcessor')
    def test_regenerate_feature_calls_processor(self, mock_proc_cls, mock_db_cls):
        """Test that regenerate feature calls the processor."""
        from src.cli import handle_regenerate_feature

        mock_db = MagicMock()
        mock_db.get_feature.return_value = {'feature_id': 'speedgrader', 'name': 'SpeedGrader'}
        mock_db.get_content_for_feature.return_value = [{'content': 'test content'}]
        mock_db_cls.return_value = mock_db

        mock_proc = MagicMock()
        mock_proc.summarize_feature_description.return_value = 'Generated description'
        mock_proc_cls.return_value = mock_proc

        result = handle_regenerate_feature('speedgrader')

        assert result == 0
        mock_proc.summarize_feature_description.assert_called_once()
        mock_db.update_feature_description.assert_called_once()

    @patch('src.cli.Database')
    def test_regenerate_feature_not_found(self, mock_db_cls):
        """Test regenerate feature with unknown ID."""
        from src.cli import handle_regenerate_feature

        mock_db = MagicMock()
        mock_db.get_feature.return_value = None
        mock_db_cls.return_value = mock_db

        result = handle_regenerate_feature('unknown_feature')

        assert result == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py::TestRegenerateFeature -v`
Expected: FAIL

**Step 3: Implement handler**

In `src/cli.py`, add:

```python
from src.utils.database import Database
from src.processor.content_processor import ContentProcessor


def handle_regenerate_feature(feature_id: str, dry_run: bool = False) -> int:
    """Handle regenerate feature command.

    Args:
        feature_id: The feature ID to regenerate.
        dry_run: If True, don't actually update.

    Returns:
        Exit code.
    """
    db = Database()

    feature = db.get_feature(feature_id)
    if not feature:
        print(f"Error: Feature '{feature_id}' not found")
        return 1

    # Get recent content for context
    content = db.get_content_for_feature(feature_id)
    content_snippet = "\n".join([
        f"- {c.get('title', '')}: {c.get('content', '')[:200]}"
        for c in content[:5]
    ]) if content else "No recent content available."

    if dry_run:
        print(f"Would regenerate description for: {feature['name']}")
        print(f"Using context from {len(content)} content items")
        return 0

    processor = ContentProcessor()
    description = processor.summarize_feature_description(
        feature_name=feature['name'],
        content_snippet=content_snippet
    )

    if description:
        db.update_feature_description(feature_id, description)
        print(f"Updated description for {feature['name']}:")
        print(f"  {description}")
    else:
        print(f"Warning: Could not generate description (LLM unavailable?)")

    db.close()
    return 0
```

Update `main()` to call handlers:

```python
def main(args: Optional[list] = None) -> int:
    parser = create_parser()
    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 1

    if parsed.command == 'regenerate':
        if parsed.regen_type == 'feature':
            return handle_regenerate_feature(parsed.feature_id)
        elif parsed.regen_type == 'features':
            return handle_regenerate_features(
                missing_only=parsed.missing,
                dry_run=parsed.dry_run
            )
        # ... other handlers

    return 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py::TestRegenerateFeature -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat(cli): implement regenerate feature command"
```

---

### Task 3.3: Implement remaining regenerate commands

**Files:**
- Modify: `src/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write tests for all regenerate commands**

```python
class TestRegenerateCommands:
    """Tests for all regenerate commands."""

    @patch('src.cli.Database')
    @patch('src.cli.ContentProcessor')
    def test_regenerate_option(self, mock_proc_cls, mock_db_cls):
        """Test regenerate option command."""
        from src.cli import handle_regenerate_option

        mock_db = MagicMock()
        mock_db.get_feature_option.return_value = {
            'option_id': 'test_opt',
            'name': 'Test Option',
            'feature_id': 'speedgrader'
        }
        mock_db.get_feature.return_value = {'name': 'SpeedGrader'}
        mock_db_cls.return_value = mock_db

        mock_proc = MagicMock()
        mock_proc.summarize_feature_option_description.return_value = 'Description'
        mock_proc_cls.return_value = mock_proc

        result = handle_regenerate_option('test_opt')
        assert result == 0
        mock_db.update_feature_option_description.assert_called_once()

    @patch('src.cli.Database')
    @patch('src.cli.ContentProcessor')
    def test_regenerate_meta_summary(self, mock_proc_cls, mock_db_cls):
        """Test regenerate meta-summary command."""
        from src.cli import handle_regenerate_meta_summary

        mock_db = MagicMock()
        mock_db.get_feature_option.return_value = {
            'option_id': 'test_opt',
            'name': 'Test Option',
            'feature_id': 'speedgrader',
            'implementation_status': 'In preview'
        }
        mock_db.get_feature.return_value = {'name': 'SpeedGrader'}
        mock_db.get_latest_content_for_option.return_value = []
        mock_db_cls.return_value = mock_db

        mock_proc = MagicMock()
        mock_proc.generate_meta_summary.return_value = 'Meta summary'
        mock_proc_cls.return_value = mock_proc

        result = handle_regenerate_meta_summary('test_opt')
        assert result == 0
        mock_db.update_feature_option_meta_summary.assert_called_once()

    @patch('src.cli.Database')
    def test_regenerate_features_missing(self, mock_db_cls):
        """Test regenerate features --missing --dry-run."""
        from src.cli import handle_regenerate_features

        mock_db = MagicMock()
        mock_db.get_features_missing_description.return_value = [
            {'feature_id': 'a', 'name': 'A'},
            {'feature_id': 'b', 'name': 'B'},
        ]
        mock_db_cls.return_value = mock_db

        result = handle_regenerate_features(missing_only=True, dry_run=True)
        assert result == 0
```

**Step 2: Run tests**

Run: `pytest tests/test_cli.py::TestRegenerateCommands -v`
Expected: FAIL

**Step 3: Implement handlers**

In `src/cli.py`, add:

```python
def handle_regenerate_option(option_id: str, dry_run: bool = False) -> int:
    """Handle regenerate option command."""
    db = Database()

    option = db.get_feature_option(option_id)
    if not option:
        print(f"Error: Option '{option_id}' not found")
        return 1

    feature = db.get_feature(option['feature_id'])
    feature_name = feature['name'] if feature else 'Unknown'

    content = db.get_latest_content_for_option(option_id, limit=3)
    raw_content = "\n".join([c.get('raw_content', c.get('content', ''))[:500] for c in content])

    if dry_run:
        print(f"Would regenerate description for: {option['name']}")
        return 0

    processor = ContentProcessor()
    description = processor.summarize_feature_option_description(
        option_name=option['name'],
        feature_name=feature_name,
        raw_content=raw_content or "Feature option for " + option['name']
    )

    if description:
        db.update_feature_option_description(option_id, description)
        print(f"Updated description for {option['name']}:")
        print(f"  {description}")

    db.close()
    return 0


def handle_regenerate_meta_summary(option_id: str, dry_run: bool = False) -> int:
    """Handle regenerate meta-summary command."""
    db = Database()

    option = db.get_feature_option(option_id)
    if not option:
        print(f"Error: Option '{option_id}' not found")
        return 1

    feature = db.get_feature(option['feature_id'])
    feature_name = feature['name'] if feature else 'Unknown'

    content = db.get_latest_content_for_option(option_id, limit=5)
    content_summaries = [
        {
            'date': c.get('first_posted', 'Unknown')[:10] if c.get('first_posted') else 'Unknown',
            'title': c.get('title', ''),
            'description': c.get('announcement_description', ''),
            'implications': c.get('implications', '')
        }
        for c in content
    ]

    if dry_run:
        print(f"Would regenerate meta_summary for: {option['name']}")
        print(f"Using {len(content_summaries)} content items")
        return 0

    processor = ContentProcessor()
    meta_summary = processor.generate_meta_summary(
        option_name=option['name'],
        feature_name=feature_name,
        implementation_status=option.get('implementation_status', ''),
        content_summaries=content_summaries
    )

    if meta_summary:
        db.update_feature_option_meta_summary(option_id, meta_summary)
        print(f"Updated meta_summary for {option['name']}:")
        print(f"  {meta_summary}")

    db.close()
    return 0


def handle_regenerate_features(missing_only: bool = False, dry_run: bool = False) -> int:
    """Handle regenerate features command."""
    db = Database()

    if missing_only:
        features = db.get_features_missing_description()
    else:
        features = db.get_all_features()

    if dry_run:
        print(f"Would regenerate {len(features)} features:")
        for f in features:
            print(f"  - {f['feature_id']}: {f['name']}")
        return 0

    processor = ContentProcessor()
    for f in features:
        content = db.get_content_for_feature(f['feature_id'])
        content_snippet = "\n".join([
            f"- {c.get('title', '')}: {c.get('content', '')[:200]}"
            for c in content[:5]
        ]) if content else ""

        description = processor.summarize_feature_description(
            feature_name=f['name'],
            content_snippet=content_snippet or f"The {f['name']} feature in Canvas LMS."
        )

        if description:
            db.update_feature_description(f['feature_id'], description)
            print(f"Updated: {f['name']}")

    db.close()
    return 0


def handle_regenerate_options(missing_only: bool = False, dry_run: bool = False) -> int:
    """Handle regenerate options command."""
    db = Database()

    if missing_only:
        options = db.get_feature_options_missing_description()
    else:
        options = db.get_all_feature_options()

    if dry_run:
        print(f"Would regenerate {len(options)} options:")
        for o in options:
            print(f"  - {o['option_id']}: {o['name']}")
        return 0

    processor = ContentProcessor()
    for o in options:
        feature = db.get_feature(o['feature_id'])
        feature_name = feature['name'] if feature else 'Unknown'

        content = db.get_latest_content_for_option(o['option_id'], limit=3)
        raw_content = "\n".join([c.get('raw_content', '')[:500] for c in content])

        description = processor.summarize_feature_option_description(
            option_name=o['name'],
            feature_name=feature_name,
            raw_content=raw_content or f"Feature option: {o['name']}"
        )

        if description:
            db.update_feature_option_description(o['option_id'], description)
            print(f"Updated: {o['name']}")

    db.close()
    return 0
```

**Step 4: Run tests**

Run: `pytest tests/test_cli.py::TestRegenerateCommands -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat(cli): implement all regenerate commands (option, meta-summary, batch)"
```

---

### Task 3.4: Implement general triage command

**Files:**
- Modify: `src/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

```python
class TestGeneralTriage:
    """Tests for general triage command."""

    def test_suggest_matches_returns_ranked_list(self):
        """Test that suggest_matches returns ranked suggestions."""
        from src.cli import suggest_matches
        from src.constants import CANVAS_FEATURES

        suggestions = suggest_matches(
            title="Tips for using SpeedGrader with large classes",
            content="Many instructors struggle with grading..."
        )

        assert len(suggestions) > 0
        assert suggestions[0]['feature_id'] == 'speedgrader'
        assert 'confidence' in suggestions[0]

    def test_suggest_matches_handles_no_match(self):
        """Test suggest_matches with unrelated content."""
        from src.cli import suggest_matches

        suggestions = suggest_matches(
            title="Random unrelated topic",
            content="This has nothing to do with Canvas features"
        )

        # Should still return something, even if low confidence
        assert isinstance(suggestions, list)

    @patch('src.cli.Database')
    def test_general_list(self, mock_db_cls):
        """Test general list command."""
        from src.cli import handle_general_list

        mock_db = MagicMock()
        mock_db.get_content_by_feature.return_value = [
            {'source_id': 'blog_123', 'title': 'Test', 'first_posted': '2026-02-01'}
        ]
        mock_db_cls.return_value = mock_db

        result = handle_general_list()
        assert result == 0
```

**Step 2: Run tests**

Run: `pytest tests/test_cli.py::TestGeneralTriage -v`
Expected: FAIL

**Step 3: Implement**

In `src/cli.py`, add:

```python
from src.constants import CANVAS_FEATURES


def suggest_matches(title: str, content: str) -> List[dict]:
    """Suggest feature matches for content using keyword matching.

    Args:
        title: Content title.
        content: Content text.

    Returns:
        List of suggestions sorted by confidence, each with:
        - feature_id: The suggested feature ID
        - feature_name: The feature name
        - confidence: 0-100 confidence score
        - keywords: List of matched keywords
    """
    combined = f"{title} {content}".lower()
    suggestions = []

    for feature_id, feature_name in CANVAS_FEATURES.items():
        if feature_id == 'general':
            continue

        keywords = []
        score = 0

        # Check feature name
        name_lower = feature_name.lower()
        if name_lower in combined:
            score += 50
            keywords.append(feature_name)

        # Check feature_id (e.g., 'speedgrader')
        if feature_id.replace('_', ' ') in combined or feature_id.replace('_', '') in combined:
            score += 40
            keywords.append(feature_id)

        # Check individual words from feature name
        for word in feature_name.split():
            if len(word) > 3 and word.lower() in combined:
                score += 10
                if word not in keywords:
                    keywords.append(word)

        # Boost if in title
        if any(kw.lower() in title.lower() for kw in keywords):
            score += 20

        if score > 0:
            suggestions.append({
                'feature_id': feature_id,
                'feature_name': feature_name,
                'confidence': min(score, 100),
                'keywords': keywords
            })

    return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)[:3]


def handle_general_list(days: Optional[int] = None) -> int:
    """Handle general list command."""
    db = Database()

    items = db.get_content_by_feature('general')

    if days:
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)
        items = [i for i in items if i.get('first_posted', '') >= cutoff.isoformat()]

    if not items:
        print("No content tagged as 'general'")
        return 0

    print(f"Found {len(items)} items tagged as 'general':\n")
    for item in items:
        date = item.get('first_posted', 'Unknown')[:10] if item.get('first_posted') else 'Unknown'
        print(f"  [{date}] {item.get('source_id', 'Unknown')}")
        print(f"    {item.get('title', 'No title')[:60]}")
        print()

    db.close()
    return 0


def handle_general_triage(auto_high: bool = False, days: Optional[int] = None, export: Optional[str] = None) -> int:
    """Handle general triage command - interactive review of general-tagged content."""
    db = Database()

    items = db.get_content_by_feature('general')

    if days:
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)
        items = [i for i in items if i.get('first_posted', '') >= cutoff.isoformat()]

    if not items:
        print("No content to triage")
        return 0

    if export:
        # Export mode - write CSV
        import csv
        with open(export, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['content_id', 'title', 'suggested_feature', 'confidence'])
            for item in items:
                suggestions = suggest_matches(item.get('title', ''), item.get('content', ''))
                top = suggestions[0] if suggestions else {'feature_id': '', 'confidence': 0}
                writer.writerow([
                    item.get('source_id'),
                    item.get('title', '')[:50],
                    top.get('feature_id', ''),
                    top.get('confidence', 0)
                ])
        print(f"Exported {len(items)} items to {export}")
        return 0

    # Interactive mode
    print(f"Reviewing {len(items)} items tagged as 'general'...\n")

    for i, item in enumerate(items):
        print(f"[{i+1}/{len(items)}] {item.get('source_id', 'Unknown')} ({item.get('first_posted', 'Unknown')[:10]})")
        print(f"Title: {item.get('title', 'No title')}")
        print(f"Preview: {item.get('content', '')[:200]}...")
        print()

        suggestions = suggest_matches(item.get('title', ''), item.get('content', ''))

        print("Suggested matches:")
        for j, s in enumerate(suggestions):
            print(f"  {j+1}. {s['feature_id']} ({s['confidence']}% confidence) - keywords: {', '.join(s['keywords'])}")
        print(f"  {len(suggestions)+1}. [skip] - keep as general")
        print(f"  {len(suggestions)+2}. [new] - create new feature/option")
        print(f"  {len(suggestions)+3}. [quit] - exit triage")

        if auto_high and suggestions and suggestions[0]['confidence'] >= 80:
            print(f"\n  Auto-assigning to {suggestions[0]['feature_id']} (confidence >= 80%)")
            db.reassign_content_feature('general', item.get('source_id'), suggestions[0]['feature_id'])
            continue

        try:
            choice = input(f"\nChoice [1-{len(suggestions)+3}]: ").strip()

            if choice == str(len(suggestions)+3) or choice.lower() == 'quit':
                print("Exiting triage")
                break
            elif choice == str(len(suggestions)+1) or choice.lower() == 'skip':
                print("Skipped\n")
                continue
            elif choice == str(len(suggestions)+2) or choice.lower() == 'new':
                print("TODO: Implement new feature/option creation")
                continue
            elif choice.isdigit() and 1 <= int(choice) <= len(suggestions):
                selected = suggestions[int(choice)-1]
                db.reassign_content_feature('general', item.get('source_id'), selected['feature_id'])
                print(f"Assigned to {selected['feature_id']}\n")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting triage")
            break

    db.close()
    return 0
```

**Step 4: Run tests**

Run: `pytest tests/test_cli.py::TestGeneralTriage -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat(cli): implement general list and triage commands with keyword matching"
```

---

## Phase 4: Scraper Updates

### Task 4.1: Parse page-level lifecycle dates from release notes

**Files:**
- Modify: `src/scrapers/instructure_community.py`
- Test: `tests/test_scrapers.py`

**Step 1: Write the failing test**

```python
class TestLifecycleDateParsing:
    """Tests for parsing lifecycle dates from release notes."""

    def test_parse_page_lifecycle_dates(self):
        """Test parsing beta and production dates from intro paragraph."""
        from scrapers.instructure_community import parse_page_lifecycle_dates

        intro = """Unless otherwise stated, all features in this release are
        available in the Beta environment on 2026-01-19 and the Production
        environment on 2026-02-21."""

        result = parse_page_lifecycle_dates(intro)

        assert result['beta_date'].isoformat() == '2026-01-19'
        assert result['production_date'].isoformat() == '2026-02-21'

    def test_parse_page_lifecycle_dates_no_match(self):
        """Test parsing when dates not found."""
        from scrapers.instructure_community import parse_page_lifecycle_dates

        intro = "This release includes various improvements."
        result = parse_page_lifecycle_dates(intro)

        assert result['beta_date'] is None
        assert result['production_date'] is None

    def test_parse_page_lifecycle_dates_alternate_format(self):
        """Test parsing alternate date formats."""
        from scrapers.instructure_community import parse_page_lifecycle_dates

        intro = """Features will be available in Beta on January 19, 2026
        and Production on February 21, 2026."""

        result = parse_page_lifecycle_dates(intro)

        # Should handle various date formats
        assert result['beta_date'] is not None or result['production_date'] is not None
```

**Step 2: Run test**

Run: `pytest tests/test_scrapers.py::TestLifecycleDateParsing -v`
Expected: FAIL

**Step 3: Implement**

In `src/scrapers/instructure_community.py`, add:

```python
import re
from datetime import date


def parse_page_lifecycle_dates(intro_text: str) -> dict:
    """Parse beta and production dates from release note intro paragraph.

    Looks for patterns like:
    - "Beta environment on 2026-01-19"
    - "Production environment on 2026-02-21"
    - "Beta on January 19, 2026"

    Args:
        intro_text: The intro paragraph text.

    Returns:
        Dict with 'beta_date' and 'production_date' (date objects or None).
    """
    result = {'beta_date': None, 'production_date': None}

    # Pattern for ISO dates: 2026-01-19
    iso_pattern = r'(\d{4}-\d{2}-\d{2})'

    # Pattern for written dates: January 19, 2026
    written_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})'

    text_lower = intro_text.lower()

    # Find beta date
    beta_match = re.search(r'beta\s+(?:environment\s+)?on\s+' + iso_pattern, text_lower)
    if beta_match:
        try:
            result['beta_date'] = date.fromisoformat(beta_match.group(1))
        except ValueError:
            pass

    if not result['beta_date']:
        beta_written = re.search(r'beta\s+(?:environment\s+)?on\s+' + written_pattern, intro_text, re.IGNORECASE)
        if beta_written:
            result['beta_date'] = _parse_written_date(beta_written.group(1), beta_written.group(2), beta_written.group(3))

    # Find production date
    prod_match = re.search(r'production\s+(?:environment\s+)?on\s+' + iso_pattern, text_lower)
    if prod_match:
        try:
            result['production_date'] = date.fromisoformat(prod_match.group(1))
        except ValueError:
            pass

    if not result['production_date']:
        prod_written = re.search(r'production\s+(?:environment\s+)?on\s+' + written_pattern, intro_text, re.IGNORECASE)
        if prod_written:
            result['production_date'] = _parse_written_date(prod_written.group(1), prod_written.group(2), prod_written.group(3))

    return result


def _parse_written_date(month_name: str, day: str, year: str) -> Optional[date]:
    """Parse a written date like 'January 19, 2026' into a date object."""
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    try:
        return date(int(year), months[month_name.lower()], int(day))
    except (ValueError, KeyError):
        return None
```

**Step 4: Run test**

Run: `pytest tests/test_scrapers.py::TestLifecycleDateParsing -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scrapers/instructure_community.py tests/test_scrapers.py
git commit -m "feat(scraper): add parse_page_lifecycle_dates for beta/production date extraction"
```

---

### Task 4.2: Scrape comments from blog/Q&A posts

**Files:**
- Modify: `src/scrapers/instructure_community.py`
- Test: `tests/test_scrapers.py`

**Step 1: Write the failing test**

```python
class TestCommentScraping:
    """Tests for scraping comments from blog/Q&A posts."""

    def test_scrape_comments_returns_list(self, mock_scraper):
        """Test that scrape_comments returns a list of comment dicts."""
        from scrapers.instructure_community import InstructureScraper

        # Mock the page content
        mock_scraper.page.content.return_value = """
        <div class="comment">
            <div class="comment-body">First comment text</div>
            <time datetime="2026-02-01T10:00:00Z"></time>
        </div>
        <div class="comment">
            <div class="comment-body">Second comment text</div>
            <time datetime="2026-02-02T10:00:00Z"></time>
        </div>
        """

        comments = mock_scraper.scrape_comments("https://example.com/post/123")

        assert isinstance(comments, list)
        # Implementation will vary based on actual DOM structure

    def test_scrape_comments_redacts_pii(self, mock_scraper):
        """Test that comments have PII redacted."""
        # The actual redaction happens when storing, but scraper should return raw
        pass  # Will be tested at integration level
```

**Step 2-5: Implementation follows similar pattern**

This task involves DOM inspection of the actual Instructure Community site to determine correct selectors. The implementation will be similar to existing scraping methods but targeting comment elements.

---

## Phase 5: Integration & Documentation

### Task 5.1: Update main.py to use new LLM methods

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main.py`

This task integrates all the new components into the main scraping flow:
- Call `parse_page_lifecycle_dates()` when scraping release notes
- Store lifecycle dates via `update_feature_option_lifecycle_dates()`
- Generate `description` and `implications` for announcements
- Trigger `meta_summary` regeneration when appropriate

### Task 5.2: Create CLI documentation

**Files:**
- Create: `docs/cli.md`

Document all CLI commands with examples.

### Task 5.3: Update database schema documentation

**Files:**
- Modify: `docs/database-schema.md`

Update the ERD and field descriptions for v2.0.

### Task 5.4: Run full test suite

**Command:**
```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass

### Task 5.5: Final commit

```bash
git add -A
git commit -m "feat: complete v2.0 LLM summarization redesign implementation"
```

---

## Summary

| Phase | Tasks | Estimated Steps |
|-------|-------|-----------------|
| 1. Database Schema | 8 tasks | ~40 steps |
| 2. Content Processor | 2 tasks | ~10 steps |
| 3. CLI Implementation | 4 tasks | ~20 steps |
| 4. Scraper Updates | 2 tasks | ~10 steps |
| 5. Integration & Docs | 5 tasks | ~15 steps |

**Total: 21 tasks, ~95 steps**

Each step is designed to be completable in 2-5 minutes following TDD methodology.
