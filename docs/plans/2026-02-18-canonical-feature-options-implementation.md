# Canonical Feature Options Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate the Canvas Feature Option Summary page as the canonical source of truth for feature options, replacing heuristic-based classification with a dedicated scraper, refactored schema, and updated API/frontend.

**Architecture:** New scraper for the canonical page feeds into a refactored `feature_options` table with `lifecycle_stage` and 4 config state columns (replacing `status`, `config_level`, `default_state`). The API drops computed status SQL in favor of reading `lifecycle_stage` directly. Frontend updates filters, pills, and adds a glossary page.

**Tech Stack:** Python 3.11+, Playwright (scraping), SQLite, FastAPI, React/TypeScript, TailwindCSS

**Design doc:** `docs/plans/2026-02-18-canonical-feature-options-design.md`

---

### Task 1: Database Schema Migration

**Files:**
- Modify: `src/utils/database.py:127-173` (schema + migration)
- Modify: `tests/test_api/conftest.py:28-50` (test schema)
- Test: `tests/test_database.py`

**Step 1: Write the failing test**

Add a test to `tests/test_database.py` that verifies the new columns exist and old columns don't.

```python
def test_feature_options_schema_has_new_columns(tmp_path):
    """Verify feature_options has lifecycle_stage and state columns, not old status/config_level/default_state."""
    import sqlite3
    from src.utils.database import Database

    db = Database(db_path=str(tmp_path / "test.db"))
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(feature_options)")
    columns = {row[1] for row in cursor.fetchall()}

    # New columns must exist
    assert 'lifecycle_stage' in columns
    assert 'prod_account_state' in columns
    assert 'prod_course_state' in columns
    assert 'beta_account_state' in columns
    assert 'beta_course_state' in columns
    assert 'source' in columns
    assert 'doc_url' in columns

    # Old columns must NOT exist
    assert 'status' not in columns
    assert 'config_level' not in columns
    assert 'default_state' not in columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::test_feature_options_schema_has_new_columns -v`
Expected: FAIL (old columns still exist, new columns missing)

**Step 3: Update the schema in `src/utils/database.py`**

Replace the `feature_options` CREATE TABLE statement (lines 127-151) with:

```python
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
                lifecycle_stage TEXT NOT NULL DEFAULT 'stable',
                prod_account_state TEXT DEFAULT 'N/A',
                prod_course_state TEXT DEFAULT 'N/A',
                beta_account_state TEXT DEFAULT 'N/A',
                beta_course_state TEXT DEFAULT 'N/A',
                source TEXT DEFAULT 'release_notes',
                doc_url TEXT,
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
```

Add migration logic after the CREATE TABLE for existing databases. Add new columns if missing, then migrate data from old columns, then drop old columns:

```python
        # Migration: Add new schema columns to feature_options
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
            ('lifecycle_stage', "TEXT DEFAULT 'stable'"),
            ('prod_account_state', "TEXT DEFAULT 'N/A'"),
            ('prod_course_state', "TEXT DEFAULT 'N/A'"),
            ('beta_account_state', "TEXT DEFAULT 'N/A'"),
            ('beta_course_state', "TEXT DEFAULT 'N/A'"),
            ('source', "TEXT DEFAULT 'release_notes'"),
            ('doc_url', 'TEXT'),
        ]
        for col_def in new_option_cols:
            col = col_def[0]
            col_type = col_def[1]
            try:
                cursor.execute(f"ALTER TABLE feature_options ADD COLUMN {col} {col_type}")
                conn.commit()
            except sqlite3.OperationalError:
                pass

        # Migration: Migrate old status → lifecycle_stage, then drop old columns
        # Check if old 'status' column still exists
        cursor.execute("PRAGMA table_info(feature_options)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if 'status' in existing_cols and 'lifecycle_stage' in existing_cols:
            # Migrate status → lifecycle_stage
            cursor.execute("""
                UPDATE feature_options SET lifecycle_stage = CASE
                    WHEN status = 'preview' THEN 'preview'
                    WHEN status IN ('optional', 'default_on', 'default_optional') THEN 'stable'
                    WHEN status = 'pending' THEN 'pending'
                    WHEN status IN ('beta', 'released') THEN 'stable'
                    WHEN status = 'delayed' THEN 'stable'
                    WHEN status = 'deprecated' THEN 'stable'
                    ELSE 'stable'
                END
                WHERE lifecycle_stage = 'stable' OR lifecycle_stage IS NULL
            """)
            # Migrate config_level + default_state → state columns (best-effort)
            if 'config_level' in existing_cols:
                cursor.execute("""
                    UPDATE feature_options SET
                        prod_account_state = CASE
                            WHEN config_level IN ('account', 'both') AND default_state = 'disabled' THEN 'disabled_unlocked'
                            WHEN config_level IN ('account', 'both') AND default_state = 'enabled' THEN 'enabled_unlocked'
                            WHEN config_level IN ('account', 'both') THEN 'disabled_unlocked'
                            ELSE 'N/A'
                        END,
                        prod_course_state = CASE
                            WHEN config_level IN ('course', 'both') THEN 'disabled'
                            ELSE 'N/A'
                        END
                    WHERE prod_account_state = 'N/A' AND prod_course_state = 'N/A'
                """)
            conn.commit()

            # Recreate table without old columns (SQLite doesn't support DROP COLUMN before 3.35)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feature_options_new (
                    option_id TEXT PRIMARY KEY,
                    feature_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    canonical_name TEXT,
                    description TEXT,
                    summary TEXT,
                    meta_summary TEXT,
                    meta_summary_updated_at TIMESTAMP,
                    implementation_status TEXT,
                    lifecycle_stage TEXT NOT NULL DEFAULT 'stable',
                    prod_account_state TEXT DEFAULT 'N/A',
                    prod_course_state TEXT DEFAULT 'N/A',
                    beta_account_state TEXT DEFAULT 'N/A',
                    beta_course_state TEXT DEFAULT 'N/A',
                    source TEXT DEFAULT 'release_notes',
                    doc_url TEXT,
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
            cursor.execute("""
                INSERT OR IGNORE INTO feature_options_new
                SELECT option_id, feature_id, name, canonical_name, description, summary,
                       meta_summary, meta_summary_updated_at, implementation_status,
                       lifecycle_stage, prod_account_state, prod_course_state,
                       beta_account_state, beta_course_state, source, doc_url,
                       user_group_url, beta_date, production_date, deprecation_date,
                       first_announced, last_updated, first_seen, last_seen, llm_generated_at
                FROM feature_options
            """)
            cursor.execute("DROP TABLE feature_options")
            cursor.execute("ALTER TABLE feature_options_new RENAME TO feature_options")
            conn.commit()
```

**Step 4: Update test fixture schema in `tests/test_api/conftest.py`**

Replace the `feature_options` CREATE TABLE in the test fixture (lines 28-50) to match the new schema:

```python
        CREATE TABLE feature_options (
            option_id TEXT PRIMARY KEY,
            feature_id TEXT NOT NULL,
            canonical_name TEXT,
            name TEXT NOT NULL,
            description TEXT,
            meta_summary TEXT,
            meta_summary_updated_at TIMESTAMP,
            implementation_status TEXT,
            lifecycle_stage TEXT NOT NULL DEFAULT 'stable',
            prod_account_state TEXT DEFAULT 'N/A',
            prod_course_state TEXT DEFAULT 'N/A',
            beta_account_state TEXT DEFAULT 'N/A',
            beta_course_state TEXT DEFAULT 'N/A',
            source TEXT DEFAULT 'release_notes',
            doc_url TEXT,
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
        );
```

Update the sample data INSERT (line 184-188) to use new columns:

```sql
        INSERT INTO feature_options (option_id, feature_id, canonical_name, name, lifecycle_stage, prod_account_state, prod_course_state, beta_date, production_date, description, meta_summary)
        VALUES
            ('document_processor', 'assignments', 'Document Processor', 'Document Processing App', 'preview', 'disabled_unlocked', 'N/A', '2026-03-01', '2026-03-15', 'Enables document annotation', 'Feature is in preview. Available in beta March 1.'),
            ('enhanced_filters', 'gradebook', 'Enhanced Gradebook Filters', 'Enhanced Filters', 'stable', 'disabled_unlocked', 'disabled', NULL, '2026-01-15', 'Additional filtering options', 'Feature is available and optional.'),
            ('speedgrader_sort', 'speedgrader', 'Sort by Student Name', 'Sort by Name', 'stable', 'enabled_unlocked', 'N/A', NULL, '2025-12-01', 'Sort submissions alphabetically', 'Feature is fully released.');
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_database.py::test_feature_options_schema_has_new_columns -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/utils/database.py tests/test_database.py tests/test_api/conftest.py
git commit -m "feat: migrate feature_options schema to lifecycle_stage and config state columns"
```

---

### Task 2: Update `upsert_feature_option` Method

**Files:**
- Modify: `src/utils/database.py:791-846` (upsert method)

**Step 1: Write the failing test**

Add to `tests/test_database.py`:

```python
def test_upsert_feature_option_with_new_fields(tmp_path):
    """Test upserting a feature option with lifecycle_stage and state columns."""
    from src.utils.database import Database

    db = Database(db_path=str(tmp_path / "test.db"))
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO features (feature_id, name) VALUES ('assignments', 'Assignments')")
    conn.commit()

    db.upsert_feature_option(
        option_id='test_option',
        feature_id='assignments',
        name='Test Option',
        canonical_name='Test Option',
        lifecycle_stage='preview',
        prod_account_state='disabled_unlocked',
        prod_course_state='N/A',
        source='canonical_page',
    )

    cursor.execute("SELECT * FROM feature_options WHERE option_id = 'test_option'")
    row = dict(cursor.fetchone())
    assert row['lifecycle_stage'] == 'preview'
    assert row['prod_account_state'] == 'disabled_unlocked'
    assert row['prod_course_state'] == 'N/A'
    assert row['source'] == 'canonical_page'
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::test_upsert_feature_option_with_new_fields -v`
Expected: FAIL (method signature doesn't accept new params)

**Step 3: Update the `upsert_feature_option` method**

Replace the method signature and SQL at `src/utils/database.py:791-846`:

```python
    def upsert_feature_option(
        self,
        option_id: str,
        feature_id: str,
        name: str,
        canonical_name: str = None,
        summary: str = None,
        lifecycle_stage: str = 'stable',
        prod_account_state: str = 'N/A',
        prod_course_state: str = 'N/A',
        beta_account_state: str = 'N/A',
        beta_course_state: str = 'N/A',
        source: str = 'release_notes',
        doc_url: str = None,
        user_group_url: str = None,
        first_announced: str = None,
    ) -> None:
        """Create or update a feature option record.

        Args:
            option_id: Slugified unique ID.
            feature_id: FK to features table.
            name: Display name.
            canonical_name: Exact name from canonical source.
            summary: Description or raw content excerpt.
            lifecycle_stage: 'preview', 'stable', or 'pending'.
            prod_account_state: Production account config state.
            prod_course_state: Production course config state.
            beta_account_state: Beta account config state.
            beta_course_state: Beta course config state.
            source: 'canonical_page' or 'release_notes'.
            doc_url: Documentation URL.
            user_group_url: URL to Feature Preview community user group.
            first_announced: When first announced (ISO timestamp).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO feature_options
                (option_id, feature_id, name, canonical_name, summary,
                 lifecycle_stage, prod_account_state, prod_course_state,
                 beta_account_state, beta_course_state, source, doc_url,
                 user_group_url, first_announced, last_updated, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(option_id) DO UPDATE SET
                name = COALESCE(excluded.name, feature_options.name),
                canonical_name = COALESCE(excluded.canonical_name, feature_options.canonical_name),
                summary = COALESCE(excluded.summary, feature_options.summary),
                lifecycle_stage = CASE
                    WHEN excluded.source = 'canonical_page' THEN excluded.lifecycle_stage
                    ELSE COALESCE(feature_options.lifecycle_stage, excluded.lifecycle_stage)
                END,
                prod_account_state = CASE
                    WHEN excluded.source = 'canonical_page' THEN excluded.prod_account_state
                    ELSE COALESCE(feature_options.prod_account_state, excluded.prod_account_state)
                END,
                prod_course_state = CASE
                    WHEN excluded.source = 'canonical_page' THEN excluded.prod_course_state
                    ELSE COALESCE(feature_options.prod_course_state, excluded.prod_course_state)
                END,
                beta_account_state = CASE
                    WHEN excluded.source = 'canonical_page' THEN excluded.beta_account_state
                    ELSE COALESCE(feature_options.beta_account_state, excluded.beta_account_state)
                END,
                beta_course_state = CASE
                    WHEN excluded.source = 'canonical_page' THEN excluded.beta_course_state
                    ELSE COALESCE(feature_options.beta_course_state, excluded.beta_course_state)
                END,
                source = CASE
                    WHEN excluded.source = 'canonical_page' THEN 'canonical_page'
                    ELSE feature_options.source
                END,
                doc_url = COALESCE(excluded.doc_url, feature_options.doc_url),
                user_group_url = COALESCE(excluded.user_group_url, feature_options.user_group_url),
                last_updated = ?,
                last_seen = ?
        """, (
            option_id, feature_id, name, canonical_name, summary,
            lifecycle_stage, prod_account_state, prod_course_state,
            beta_account_state, beta_course_state, source, doc_url,
            user_group_url, first_announced, now, now, now, now, now
        ))
        conn.commit()
```

Note the upsert priority: when `source = 'canonical_page'`, canonical fields overwrite. When `source = 'release_notes'`, existing canonical values are preserved.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::test_upsert_feature_option_with_new_fields -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat: update upsert_feature_option for new schema columns"
```

---

### Task 3: Update `classify_release_features` Caller

**Files:**
- Modify: `src/scrapers/instructure_community.py:2375-2388` (the `upsert_feature_option` call site)

**Step 1: Update the call to `upsert_feature_option` in `classify_release_features`**

At line 2379, the call passes `status='pending'`, `config_level=...`, `default_state=...`. Update to use new params:

```python
                db.upsert_feature_option(
                    option_id=entity_id,
                    feature_id=feature_id,
                    name=feature.name,
                    canonical_name=canonical_name,
                    lifecycle_stage='stable',  # Will be overwritten by canonical scraper
                    source='release_notes',
                    first_announced=announced_at,
                )
```

Note: we no longer pass config state from release notes — the canonical page is authoritative for that. We pass `source='release_notes'` so the upsert logic knows not to overwrite canonical fields.

**Step 2: Find and update `classify_deploy_changes` similarly**

Search for the other `upsert_feature_option` call in `classify_deploy_changes` (~line 2498-2653) and apply the same change.

**Step 3: Update any other callers of `upsert_feature_option`**

Search the codebase for all calls to `upsert_feature_option` and verify they pass the new params. Check:
- `src/utils/database.py` (the method itself)
- `src/scrapers/instructure_community.py` (classify_release_features, classify_deploy_changes)
- Any scripts in `scripts/`

**Step 4: Run existing tests**

Run: `pytest tests/ -v --tb=short`
Expected: All pass (or failures only in tests being updated in next tasks)

**Step 5: Commit**

```bash
git add src/scrapers/instructure_community.py
git commit -m "refactor: update release note classifier to use new feature_option schema"
```

---

### Task 4: Canonical Page Scraper

**Files:**
- Create: `src/scrapers/canonical_options.py`
- Test: `tests/test_canonical_options.py`

**Step 1: Write the failing test for config text parsing**

Create `tests/test_canonical_options.py`:

```python
"""Tests for canonical feature options page scraper."""
import pytest
from src.scrapers.canonical_options import parse_config_text


class TestParseConfigText:
    """Test parsing configuration text into state columns."""

    def test_account_disabled_unlocked(self):
        result = parse_config_text("Account (Disabled/Unlocked)")
        assert result == {
            'prod_account_state': 'disabled_unlocked',
            'prod_course_state': 'N/A',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_account_course_disabled_unlocked(self):
        result = parse_config_text("Account/Course (Disabled/Unlocked)")
        assert result == {
            'prod_account_state': 'disabled_unlocked',
            'prod_course_state': 'disabled',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_account_disabled_locked(self):
        result = parse_config_text("Account (Disabled/Locked)")
        assert result == {
            'prod_account_state': 'disabled_locked',
            'prod_course_state': 'N/A',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_account_only_no_lock(self):
        result = parse_config_text("Account (Disabled)")
        assert result == {
            'prod_account_state': 'disabled',
            'prod_course_state': 'N/A',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_course_only_disabled(self):
        result = parse_config_text("Course (Disabled)")
        assert result == {
            'prod_account_state': 'N/A',
            'prod_course_state': 'disabled',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_beta_vs_production(self):
        result = parse_config_text("Beta: Account/Course (Enabled/Unlocked); Production: Account/Course (Disabled/Unlocked)")
        assert result == {
            'prod_account_state': 'disabled_unlocked',
            'prod_course_state': 'disabled',
            'beta_account_state': 'enabled_unlocked',
            'beta_course_state': 'enabled',
        }

    def test_mixed_account_locked_course_disabled(self):
        result = parse_config_text("Account (Disabled/Locked); Course (Disabled)")
        assert result == {
            'prod_account_state': 'disabled_locked',
            'prod_course_state': 'disabled',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_csm_managed(self):
        result = parse_config_text("Must be configured by a Customer Success Manager (CSM)")
        assert result == {
            'prod_account_state': 'csm_managed',
            'prod_course_state': 'N/A',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_lti_required(self):
        result = parse_config_text("LTI Configuration Required")
        assert result == {
            'prod_account_state': 'lti_required',
            'prod_course_state': 'N/A',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_user_setting(self):
        result = parse_config_text("User Settings (Disabled)")
        assert result == {
            'prod_account_state': 'user_setting',
            'prod_course_state': 'N/A',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_enabled_by_default(self):
        """Default Optional entries just say 'Enabled by default'."""
        result = parse_config_text("Enabled by default")
        assert result == {
            'prod_account_state': 'enabled_unlocked',
            'prod_course_state': 'N/A',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }

    def test_account_enabled(self):
        result = parse_config_text("Account (Enabled)")
        assert result == {
            'prod_account_state': 'enabled',
            'prod_course_state': 'N/A',
            'beta_account_state': 'N/A',
            'beta_course_state': 'N/A',
        }
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_canonical_options.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Implement `parse_config_text` in `src/scrapers/canonical_options.py`**

```python
"""Scraper for the Canvas Feature Option Summary canonical page."""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# Canonical page URL
CANONICAL_OPTIONS_URL = "https://community.instructure.com/en/kb/articles/531316-unknown"


def parse_config_text(text: str) -> Dict[str, str]:
    """Parse configuration text into the 4 state columns.

    Handles formats like:
        "Account (Disabled/Unlocked)"
        "Account/Course (Disabled/Unlocked)"
        "Beta: Account/Course (Enabled/Unlocked); Production: Account/Course (Disabled/Unlocked)"
        "Account (Disabled/Locked); Course (Disabled)"
        "Account (Disabled)"
        "Must be configured by a Customer Success Manager (CSM)"
        "LTI Configuration Required"
        "User Settings (Disabled)"
        "Enabled by default"

    Returns:
        Dict with keys: prod_account_state, prod_course_state,
                        beta_account_state, beta_course_state
    """
    result = {
        'prod_account_state': 'N/A',
        'prod_course_state': 'N/A',
        'beta_account_state': 'N/A',
        'beta_course_state': 'N/A',
    }

    text = text.strip()

    # Special cases
    if 'Customer Success Manager' in text or 'CSM' in text:
        result['prod_account_state'] = 'csm_managed'
        return result
    if 'LTI Configuration Required' in text:
        result['prod_account_state'] = 'lti_required'
        return result
    if text.startswith('User Settings'):
        result['prod_account_state'] = 'user_setting'
        return result
    if text == 'Enabled by default':
        result['prod_account_state'] = 'enabled_unlocked'
        return result

    # Check for Beta/Production split
    if 'Beta:' in text and 'Production:' in text:
        parts = re.split(r';\s*Production:\s*', text, maxsplit=1)
        beta_part = parts[0].replace('Beta:', '').strip()
        prod_part = parts[1].strip() if len(parts) > 1 else ''

        beta_states = _parse_single_config(beta_part)
        prod_states = _parse_single_config(prod_part)

        result['beta_account_state'] = beta_states.get('account', 'N/A')
        result['beta_course_state'] = beta_states.get('course', 'N/A')
        result['prod_account_state'] = prod_states.get('account', 'N/A')
        result['prod_course_state'] = prod_states.get('course', 'N/A')
        return result

    # Check for multi-part (e.g., "Account (Disabled/Locked); Course (Disabled)")
    if ';' in text:
        for part in text.split(';'):
            part = part.strip()
            states = _parse_single_config(part)
            if 'account' in states:
                result['prod_account_state'] = states['account']
            if 'course' in states:
                result['prod_course_state'] = states['course']
        return result

    # Single config
    states = _parse_single_config(text)
    if 'account' in states:
        result['prod_account_state'] = states['account']
    if 'course' in states:
        result['prod_course_state'] = states['course']

    return result


def _parse_single_config(text: str) -> Dict[str, str]:
    """Parse a single config segment like 'Account/Course (Disabled/Unlocked)'.

    Returns dict with 'account' and/or 'course' keys.
    """
    result = {}
    text = text.strip()

    # Extract level(s) and state from format: "Level (State)"
    match = re.match(r'^([\w/]+)\s*\(([^)]+)\)', text)
    if not match:
        return result

    levels_str = match.group(1).lower()
    state_str = match.group(2).strip()

    # Parse state: "Disabled/Unlocked" → "disabled_unlocked", "Disabled" → "disabled"
    state_parts = [p.strip().lower() for p in state_str.split('/')]
    if len(state_parts) == 2:
        state = f"{state_parts[0]}_{state_parts[1]}"
    else:
        state = state_parts[0]

    # Determine account state (with lock info) and course state (no lock)
    has_account = 'account' in levels_str
    has_course = 'course' in levels_str

    if has_account:
        result['account'] = state

    if has_course:
        # Course level has no lock concept - strip lock suffix
        course_state = state_parts[0]  # just enabled/disabled
        result['course'] = course_state

    return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_canonical_options.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scrapers/canonical_options.py tests/test_canonical_options.py
git commit -m "feat: add config text parser for canonical feature options page"
```

---

### Task 5: Canonical Page HTML Scraper

**Files:**
- Modify: `src/scrapers/canonical_options.py` (add scraping logic)
- Test: `tests/test_canonical_options.py` (add scraper tests with mock HTML)

**Step 1: Write a test with mock HTML**

Add to `tests/test_canonical_options.py`:

```python
from src.scrapers.canonical_options import parse_canonical_page_html, CanonicalOption


MOCK_HTML = """
<html><body>
<h2>Pending Feature Options</h2>
<table><tbody>
<tr><td><a href="https://docs.example.com/new-quizzes">New Quizzes</a></td>
<td>Assessment engine replacing Classic Quizzes</td>
<td>Account (Disabled/Unlocked)</td></tr>
</tbody></table>

<h2>Optional Features</h2>
<table><tbody>
<tr><td><a href="https://docs.example.com/anon-grading">Anonymous Grading</a></td>
<td>Allow assignments to be graded anonymously</td>
<td>Account/Course (Disabled/Unlocked)</td></tr>
</tbody></table>

<h2>Default Optional Features</h2>
<table><tbody>
<tr><td><a href="https://docs.example.com/comment-lib">Comment Library</a></td>
<td>Save frequently used feedback</td>
<td>Enabled by default</td></tr>
</tbody></table>

<h2>Feature Previews</h2>
<table><tbody>
<tr><td><a href="https://docs.example.com/enhanced-rubrics">Enhanced Rubrics</a></td>
<td>Visual enhancements to rubrics</td>
<td>Beta: Account/Course (Enabled/Unlocked); Production: Account/Course (Disabled/Unlocked)</td>
<td><a href="https://community.example.com/rubrics-group">Enhanced Rubrics User Group</a></td></tr>
</tbody></table>
</body></html>
"""


class TestParseCanonicalPageHtml:

    def test_parses_pending(self):
        options = parse_canonical_page_html(MOCK_HTML)
        pending = [o for o in options if o.lifecycle_stage == 'pending']
        assert len(pending) == 1
        assert pending[0].name == 'New Quizzes'
        assert pending[0].prod_account_state == 'disabled_unlocked'

    def test_parses_optional(self):
        options = parse_canonical_page_html(MOCK_HTML)
        stable = [o for o in options if o.name == 'Anonymous Grading']
        assert len(stable) == 1
        assert stable[0].lifecycle_stage == 'stable'
        assert stable[0].prod_account_state == 'disabled_unlocked'
        assert stable[0].prod_course_state == 'disabled'

    def test_parses_default_optional(self):
        options = parse_canonical_page_html(MOCK_HTML)
        default_opt = [o for o in options if o.name == 'Comment Library']
        assert len(default_opt) == 1
        assert default_opt[0].lifecycle_stage == 'stable'
        assert default_opt[0].prod_account_state == 'enabled_unlocked'

    def test_parses_preview_with_beta_prod_split(self):
        options = parse_canonical_page_html(MOCK_HTML)
        preview = [o for o in options if o.name == 'Enhanced Rubrics']
        assert len(preview) == 1
        assert preview[0].lifecycle_stage == 'preview'
        assert preview[0].beta_account_state == 'enabled_unlocked'
        assert preview[0].prod_account_state == 'disabled_unlocked'

    def test_total_count(self):
        options = parse_canonical_page_html(MOCK_HTML)
        assert len(options) == 4
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_canonical_options.py::TestParseCanonicalPageHtml -v`
Expected: FAIL

**Step 3: Implement the HTML parser**

Add to `src/scrapers/canonical_options.py`:

```python
from bs4 import BeautifulSoup


@dataclass
class CanonicalOption:
    """A feature option parsed from the canonical page."""
    name: str
    description: str
    lifecycle_stage: str  # 'preview', 'stable', 'pending'
    prod_account_state: str = 'N/A'
    prod_course_state: str = 'N/A'
    beta_account_state: str = 'N/A'
    beta_course_state: str = 'N/A'
    doc_url: Optional[str] = None
    user_group_url: Optional[str] = None


# Section heading → lifecycle_stage mapping
SECTION_LIFECYCLE_MAP = {
    'pending feature options': 'pending',
    'optional features': 'stable',
    'default optional features': 'stable',
    'feature previews': 'preview',
}


def parse_canonical_page_html(html: str) -> List[CanonicalOption]:
    """Parse the canonical feature options page HTML into structured data.

    Args:
        html: Raw HTML of the canonical page.

    Returns:
        List of CanonicalOption dataclasses.
    """
    soup = BeautifulSoup(html, 'html.parser')
    options: List[CanonicalOption] = []

    # Find all H2 section headings
    for h2 in soup.find_all('h2'):
        heading_text = h2.get_text(strip=True).lower()
        lifecycle_stage = None

        for section_key, stage in SECTION_LIFECYCLE_MAP.items():
            if section_key in heading_text:
                lifecycle_stage = stage
                break

        if lifecycle_stage is None:
            continue

        # Find the table following this H2
        table = h2.find_next('table')
        if not table:
            continue

        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 3:
                continue

            # Cell 0: Name (may contain a link)
            name_cell = cells[0]
            name_link = name_cell.find('a')
            name = name_cell.get_text(strip=True)
            doc_url = name_link['href'] if name_link and name_link.has_attr('href') else None

            # Cell 1: Description
            description = cells[1].get_text(strip=True)

            # Cell 2: Configuration text
            config_text = cells[2].get_text(strip=True)
            config = parse_config_text(config_text)

            # Cell 3 (optional): User group link (for previews)
            user_group_url = None
            if len(cells) > 3:
                group_link = cells[3].find('a')
                if group_link and group_link.has_attr('href'):
                    user_group_url = group_link['href']

            options.append(CanonicalOption(
                name=name,
                description=description,
                lifecycle_stage=lifecycle_stage,
                doc_url=doc_url,
                user_group_url=user_group_url,
                **config,
            ))

    return options
```

Note: The actual page HTML structure may differ from this mock. The scraper should be adapted during implementation to match the real page structure. Use Playwright to fetch the page and inspect the actual DOM. The parser above provides the correct interface; the HTML extraction logic may need adjustment.

**Step 4: Run tests**

Run: `pytest tests/test_canonical_options.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scrapers/canonical_options.py tests/test_canonical_options.py
git commit -m "feat: add canonical page HTML parser for feature options"
```

---

### Task 6: Canonical Scraper Integration (Playwright + DB Upsert)

**Files:**
- Modify: `src/scrapers/canonical_options.py` (add `scrape_canonical_options` function)
- Modify: `src/main.py` (add to scraping schedule)

**Step 1: Add the Playwright scraping function**

Add to `src/scrapers/canonical_options.py`:

```python
async def scrape_canonical_options(db: "Database") -> List[CanonicalOption]:
    """Scrape the canonical feature options page and upsert into database.

    Args:
        db: Database instance.

    Returns:
        List of parsed CanonicalOption entries.
    """
    from playwright.async_api import async_playwright
    from src.scrapers.instructure_community import _slugify

    logger.info(f"Scraping canonical feature options page: {CANONICAL_OPTIONS_URL}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(CANONICAL_OPTIONS_URL, wait_until='networkidle')
        html = await page.content()
        await browser.close()

    options = parse_canonical_page_html(html)
    logger.info(f"Parsed {len(options)} feature options from canonical page")

    for option in options:
        option_id = _slugify(option.name)

        db.upsert_feature_option(
            option_id=option_id,
            feature_id=_match_feature_from_name(option.name),
            name=option.name,
            canonical_name=option.name,
            lifecycle_stage=option.lifecycle_stage,
            prod_account_state=option.prod_account_state,
            prod_course_state=option.prod_course_state,
            beta_account_state=option.beta_account_state,
            beta_course_state=option.beta_course_state,
            source='canonical_page',
            doc_url=option.doc_url,
            user_group_url=option.user_group_url,
        )

    return options
```

The `_match_feature_from_name` helper should attempt to match the option name to a canonical feature_id (e.g., "Enhanced Rubrics" → "rubrics"). Reuse the existing `_match_feature_id` function from `instructure_community.py` or use a simple name-based lookup.

**Step 2: Wire into `src/main.py`**

Find where the other scrapers are called and add canonical options scraping alongside them on the same schedule. Typically something like:

```python
from src.scrapers.canonical_options import scrape_canonical_options

# In the main scraping pipeline, add:
await scrape_canonical_options(db)
```

**Step 3: Test manually**

Run: `python -c "import asyncio; from src.scrapers.canonical_options import scrape_canonical_options; from src.utils.database import Database; db = Database(); asyncio.run(scrape_canonical_options(db))"`

Verify options are inserted by checking the database.

**Step 4: Commit**

```bash
git add src/scrapers/canonical_options.py src/main.py
git commit -m "feat: integrate canonical options scraper into pipeline"
```

---

### Task 7: API Layer Updates

**Files:**
- Modify: `src/api/database.py` (remove OPTION_STATUS_SQL, add availability helper)
- Modify: `src/api/routes/options.py` (update queries and response shape)
- Modify: `src/api/routes/features.py` (update embedded option queries)
- Test: `tests/test_api/test_options.py` (update assertions)

**Step 1: Update `src/api/database.py`**

Remove `OPTION_STATUS_SQL` and `_computed_status` for options. Keep `SETTING_STATUS_SQL` (settings are unchanged). Add an availability helper:

```python
def compute_availability(beta_date: str | None, production_date: str | None) -> str:
    """Compute availability label from dates.

    Returns one of: 'in_production', 'in_beta', 'upcoming_production',
                    'upcoming_beta', 'no_dates'
    """
    from datetime import date
    today = date.today().isoformat()

    if production_date and production_date <= today:
        return 'in_production'
    if beta_date and beta_date <= today:
        if production_date:
            return 'upcoming_production'
        return 'in_beta'
    if beta_date:
        return 'upcoming_beta'
    return 'no_dates'
```

**Step 2: Update `src/api/routes/options.py`**

Replace the list endpoint query to use `lifecycle_stage` directly:

```python
@router.get("/options")
def get_options(
    lifecycle_stage: Optional[str] = Query(None, description="Filter by lifecycle_stage (preview, stable, pending)"),
    feature: Optional[str] = Query(None, description="Filter by feature_id"),
    sort: Optional[Literal["updated", "alphabetical", "beta_date", "production_date"]] = Query("updated"),
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT
                fo.option_id, fo.feature_id, fo.canonical_name, fo.name,
                fo.description, fo.lifecycle_stage,
                fo.prod_account_state, fo.prod_course_state,
                fo.beta_account_state, fo.beta_course_state,
                fo.beta_date, fo.production_date, fo.deprecation_date,
                fo.user_group_url, fo.doc_url, fo.source,
                fo.last_updated,
                f.name as feature_name
            FROM feature_options fo
            JOIN features f ON fo.feature_id = f.feature_id
            WHERE 1=1
        """
        params = []
        if lifecycle_stage:
            query += " AND fo.lifecycle_stage = ?"
            params.append(lifecycle_stage)
        if feature:
            query += " AND fo.feature_id = ?"
            params.append(feature)
        # (sort logic unchanged)
        ...
```

Update the detail endpoint similarly, removing `OPTION_STATUS_SQL` and returning new fields. Replace the `configuration` dict:

```python
            "configuration": {
                "prod_account_state": option["prod_account_state"],
                "prod_course_state": option["prod_course_state"],
                "beta_account_state": option["beta_account_state"],
                "beta_course_state": option["beta_course_state"],
            },
```

**Step 3: Update `src/api/routes/features.py`**

Replace `OPTION_STATUS_SQL` references with `fo.lifecycle_stage` in the count queries:

```python
SUM(CASE WHEN fo.lifecycle_stage = 'preview' THEN 1 ELSE 0 END) as preview_count,
SUM(CASE WHEN fo.lifecycle_stage = 'pending' THEN 1 ELSE 0 END) as pending_count,
SUM(CASE WHEN fo.lifecycle_stage = 'stable' THEN 1 ELSE 0 END) as stable_count,
```

**Step 4: Update test assertions in `tests/test_api/test_options.py`**

Update assertions to check `lifecycle_stage` instead of `status`:

```python
def test_get_options_list(client, populated_db):
    response = client.get("/api/options")
    assert response.status_code == 200
    data = response.json()
    assert len(data["options"]) == 3

    doc_processor = next(o for o in data["options"] if o["option_id"] == "document_processor")
    assert doc_processor["lifecycle_stage"] == "preview"
    assert "status" not in doc_processor


def test_get_options_filtered_by_lifecycle_stage(client, populated_db):
    response = client.get("/api/options?lifecycle_stage=preview")
    assert response.status_code == 200
    data = response.json()
    assert len(data["options"]) == 1
    assert data["options"][0]["option_id"] == "document_processor"
```

**Step 5: Run all API tests**

Run: `pytest tests/test_api/ -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/api/database.py src/api/routes/options.py src/api/routes/features.py tests/test_api/
git commit -m "feat: update API to use lifecycle_stage instead of computed status"
```

---

### Task 8: Frontend TypeScript Types and API Client

**Files:**
- Modify: `frontend/src/types/index.ts` (update FeatureOption interfaces)
- Modify: `frontend/src/api/client.ts` (update params)

**Step 1: Update `FeatureOption` type**

Replace `status`, `config_level`, `default_state` with new fields:

```typescript
export interface FeatureOption {
  option_id: string;
  feature_id: string;
  canonical_name: string | null;
  name: string;
  description: string | null;
  meta_summary: string | null;
  lifecycle_stage: string;  // 'preview' | 'stable' | 'pending'
  prod_account_state: string;
  prod_course_state: string;
  beta_account_state: string;
  beta_course_state: string;
  beta_date: string | null;
  production_date: string | null;
  deprecation_date: string | null;
  user_group_url: string | null;
  doc_url: string | null;
  source: string | null;
  first_seen: string | null;
  last_seen: string | null;
  feature_name?: string;
}
```

Update `FeatureOptionDetail.configuration`:

```typescript
export interface FeatureOptionDetail extends FeatureOption {
  feature: {
    feature_id: string;
    name: string;
    description: string | null;
  };
  configuration: {
    prod_account_state: string;
    prod_course_state: string;
    beta_account_state: string;
    beta_course_state: string;
    // Announcement-level config (from latest announcement)
    enable_location_account: string | null;
    enable_location_course: string | null;
    subaccount_config: boolean | null;
    permissions: string | null;
    affected_areas: string | null;
    affects_ui: boolean | null;
  };
  announcements: Announcement[];
  community_posts: CommunityPost[];
}
```

**Step 2: Update API client params**

In `frontend/src/api/client.ts`, update the options list params:

```typescript
export const optionsApi = {
  list: async (params?: {
    lifecycle_stage?: string;  // was: status
    feature?: string;
    sort?: string;
  }): Promise<{ options: FeatureOption[] }> => {
    const { data } = await api.get('/options', { params });
    return data;
  },
  ...
```

**Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: update frontend types for lifecycle_stage schema"
```

---

### Task 9: Frontend StatusPill and StatusFilter Updates

**Files:**
- Modify: `frontend/src/components/StatusPill.tsx` (update config for lifecycle stages)
- Modify: `frontend/src/components/StatusFilter.tsx` (update filter options)

**Step 1: Update StatusPill config**

The `statusConfig` in `StatusPill.tsx` should map lifecycle stages. Keep existing entries for backwards compatibility with settings/other uses, but add lifecycle stage entries:

```typescript
const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  preview: { label: 'Preview', color: 'text-status-preview', bg: 'bg-status-preview/15' },
  stable: { label: 'Stable', color: 'text-status-released', bg: 'bg-status-released/15' },
  pending: { label: 'Pending', color: 'text-amber-400', bg: 'bg-amber-400/15' },
  // Keep existing for feature_settings and other uses
  beta: { label: 'Beta', color: 'text-status-beta', bg: 'bg-status-beta/15' },
  active: { label: 'Active', color: 'text-status-released', bg: 'bg-status-released/15' },
  ...
}
```

**Step 2: Update StatusFilter options**

Replace `STATUS_OPTIONS` in `StatusFilter.tsx` for the options page:

```typescript
const LIFECYCLE_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'preview', label: 'Preview', color: 'bg-status-preview' },
  { value: 'stable', label: 'Stable', color: 'bg-status-released' },
  { value: 'pending', label: 'Pending', color: 'bg-amber-400' },
]
```

Consider making StatusFilter accept options as a prop so it can be reused with different option sets (lifecycle stages for options, status for settings).

**Step 3: Commit**

```bash
git add frontend/src/components/StatusPill.tsx frontend/src/components/StatusFilter.tsx
git commit -m "feat: update StatusPill and StatusFilter for lifecycle stages"
```

---

### Task 10: Frontend Options Page Update

**Files:**
- Modify: `frontend/src/pages/Options.tsx` (use lifecycle_stage filter)

**Step 1: Update filter param name**

Change `status` → `lifecycle_stage` in query params and API calls:

```typescript
const lifecycle_stage = searchParams.get('lifecycle_stage') || ''

const { data } = useQuery({
  queryKey: ['options', { lifecycle_stage, sort }],
  queryFn: () => optionsApi.list({ lifecycle_stage: lifecycle_stage || undefined, sort }),
})
```

**Step 2: Update OptionRow to use `lifecycle_stage`**

```typescript
<StatusPill status={option.lifecycle_stage} size="sm" showDot={false} />
```

**Step 3: Commit**

```bash
git add frontend/src/pages/Options.tsx
git commit -m "feat: update Options page to filter by lifecycle_stage"
```

---

### Task 11: Frontend ConfigurationTable Update

**Files:**
- Modify: `frontend/src/components/ConfigurationTable.tsx` (show 4 state columns)

**Step 1: Update the Configuration interface and `buildConfigRows`**

Replace config_level/default_state rows with the 4 state columns. Format them human-readably:

```typescript
interface Configuration {
  prod_account_state: string;
  prod_course_state: string;
  beta_account_state: string;
  beta_course_state: string;
  // Announcement-level config
  enable_location_account: string | null;
  enable_location_course: string | null;
  subaccount_config: boolean | null;
  permissions: string | null;
  affected_areas: string | null;
  affects_ui: boolean | null;
}
```

Update `buildConfigRows` to show:
- "Prod Account" → formatted state
- "Prod Course" → formatted state (only if not N/A)
- "Beta Account" → formatted state (only if not N/A)
- "Beta Course" → formatted state (only if not N/A)

Add a `formatState` helper:

```typescript
function formatState(state: string): string {
  const states: Record<string, string> = {
    'enabled_unlocked': 'Enabled / Unlocked',
    'enabled_locked': 'Enabled / Locked',
    'disabled_unlocked': 'Disabled / Unlocked',
    'disabled_locked': 'Disabled / Locked',
    'enabled': 'Enabled (account-only)',
    'disabled': 'Disabled (account-only)',
    'csm_managed': 'CSM Managed',
    'lti_required': 'LTI Required',
    'user_setting': 'User Setting',
    'N/A': 'N/A',
  }
  return states[state] || state
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/ConfigurationTable.tsx
git commit -m "feat: update ConfigurationTable for 4-column state model"
```

---

### Task 12: Frontend OptionDetail Page Update

**Files:**
- Modify: `frontend/src/pages/OptionDetail.tsx` (use lifecycle_stage, show doc link)

**Step 1: Update StatusPill to use lifecycle_stage**

Change line 66 from `data.status` to `data.lifecycle_stage`.

**Step 2: Add doc link if present**

Below the user group link / description, add:

```tsx
{data.doc_url && (
  <a href={data.doc_url} target="_blank" rel="noopener noreferrer"
     className="text-xs font-mono text-signal-blue hover:text-signal-blue/80">
    Documentation ↗
  </a>
)}
```

**Step 3: Update DeploymentTimeline call**

Change `status={data.status}` to `status={data.lifecycle_stage}` (line 109).

**Step 4: Commit**

```bash
git add frontend/src/pages/OptionDetail.tsx
git commit -m "feat: update OptionDetail page for lifecycle_stage schema"
```

---

### Task 13: Glossary Page

**Files:**
- Create: `frontend/src/pages/Glossary.tsx`
- Modify: `frontend/src/App.tsx` (add route)
- Modify: `frontend/src/components/Layout.tsx` (add nav link)

**Step 1: Create the Glossary page component**

Create `frontend/src/pages/Glossary.tsx` with static content covering:
1. Lifecycle Stages (preview → stable → pending → enforced)
2. Configuration States (the full table with account vs course)
3. Special Configurations (CSM, LTI, user setting)
4. Availability (beta_date, production_date)

Use the existing card/section patterns from other pages. Style with TailwindCSS matching the existing design system.

**Step 2: Add route to `App.tsx`**

```tsx
import Glossary from './pages/Glossary'
// ...
<Route path="glossary" element={<Glossary />} />
```

**Step 3: Add nav link to `Layout.tsx`**

Add to `navLinks` array:

```typescript
{ path: '/glossary', label: 'Glossary' },
```

Update `isActive` if needed.

**Step 4: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add frontend/src/pages/Glossary.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add glossary page for feature option terminology"
```

---

### Task 14: Build, Test, and Verify End-to-End

**Files:** No new files — integration verification.

**Step 1: Run all backend tests**

Run: `pytest tests/ -v --tb=short`
Expected: All pass

**Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

**Step 3: Start server and manually verify**

```bash
# Kill any existing server
powershell -Command "Get-NetTCPConnection -State Listen -LocalPort 8986 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"

# Start server
cd /c/Users/mclea/claude/canvas-rss && python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8986
```

Verify:
- `GET /api/options` returns `lifecycle_stage` (not `status`)
- `GET /api/options?lifecycle_stage=preview` filters correctly
- `GET /api/options/{id}` returns 4 state columns in `configuration`
- Frontend Options page shows lifecycle stage pills
- Frontend OptionDetail page shows config grid
- Glossary page renders at `/glossary`

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: address integration issues from end-to-end testing"
```

---

### Task 15: Run Canonical Scraper on Live Page

**Step 1: Run the scraper against the real canonical page**

```bash
cd /c/Users/mclea/claude/canvas-rss
python -c "
import asyncio
from src.scrapers.canonical_options import scrape_canonical_options
from src.utils.database import Database
db = Database()
options = asyncio.run(scrape_canonical_options(db))
print(f'Scraped {len(options)} options')
for o in options[:5]:
    print(f'  {o.name}: {o.lifecycle_stage} | account={o.prod_account_state} course={o.prod_course_state}')
"
```

**Step 2: Verify database contents**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/canvas_digest.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT option_id, name, lifecycle_stage, prod_account_state, source FROM feature_options WHERE source = \"canonical_page\" LIMIT 10')
for row in cursor.fetchall():
    print(dict(row))
"
```

**Step 3: Adapt parser if needed**

The real page HTML may differ from mock HTML. Inspect the actual DOM structure and adjust `parse_canonical_page_html` accordingly. This is expected — the mock gives the correct interface, the real parser needs to match the actual page structure.

**Step 4: Commit any parser adjustments**

```bash
git add src/scrapers/canonical_options.py tests/test_canonical_options.py
git commit -m "fix: adapt canonical page parser to real HTML structure"
```
