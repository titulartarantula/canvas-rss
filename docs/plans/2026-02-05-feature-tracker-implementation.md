# Feature Tracker Website Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a public website for educational technologists to track Canvas LMS feature options and deployment readiness.

**Architecture:** FastAPI backend serving JSON from existing SQLite database, React frontend with client-side routing. Single Docker container serves both API (`/api/*`) and static React build (all other routes).

**Tech Stack:** FastAPI, SQLite, Vite, React 18, TypeScript, TailwindCSS, React Router

---

## Phase 1: Backend API Setup

### Task 1.1: Create FastAPI App Structure

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/main.py`
- Create: `src/api/database.py`

**Step 1: Create the API package init**

```python
# src/api/__init__.py
"""FastAPI application for Canvas Feature Tracker."""
```

**Step 2: Create database connection helper**

```python
# src/api/database.py
"""Database connection utilities for the API."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

# Default database path - can be overridden via environment variable
import os
DB_PATH = Path(os.getenv("DATABASE_PATH", "data/canvas_digest.db"))


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a dictionary."""
    return dict(row) if row else None


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    """Convert a list of sqlite3.Row to a list of dictionaries."""
    return [dict(row) for row in rows]
```

**Step 3: Create FastAPI main app**

```python
# src/api/main.py
"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(
    title="Canvas Feature Tracker API",
    description="API for tracking Canvas LMS feature options and deployment readiness",
    version="1.0.0",
)

# Static files will be mounted after frontend build exists
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# Serve frontend for all non-API routes (after routes are registered)
# This will be configured after frontend is built
```

**Step 4: Commit**

```bash
git add src/api/
git commit -m "feat(api): create FastAPI app structure with database helper"
```

---

### Task 1.2: Create API Tests Infrastructure

**Files:**
- Create: `tests/test_api/__init__.py`
- Create: `tests/test_api/conftest.py`
- Create: `tests/test_api/test_health.py`

**Step 1: Create test package**

```python
# tests/test_api/__init__.py
"""API tests package."""
```

**Step 2: Create test fixtures**

```python
# tests/test_api/conftest.py
"""Pytest fixtures for API tests."""
import pytest
import sqlite3
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.main import app
from src.api import database


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with schema."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)

    # Create schema (minimal for tests)
    conn.executescript("""
        CREATE TABLE features (
            feature_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            llm_generated_at TIMESTAMP
        );

        CREATE TABLE feature_options (
            option_id TEXT PRIMARY KEY,
            feature_id TEXT NOT NULL,
            canonical_name TEXT,
            name TEXT NOT NULL,
            description TEXT,
            meta_summary TEXT,
            meta_summary_updated_at TIMESTAMP,
            implementation_status TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            beta_date DATE,
            production_date DATE,
            deprecation_date DATE,
            config_level TEXT,
            default_state TEXT,
            user_group_url TEXT,
            first_announced TIMESTAMP,
            last_updated TIMESTAMP,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            llm_generated_at TIMESTAMP,
            FOREIGN KEY (feature_id) REFERENCES features(feature_id)
        );

        CREATE TABLE content_items (
            id INTEGER PRIMARY KEY,
            source_id TEXT UNIQUE,
            url TEXT,
            title TEXT,
            content_type TEXT,
            summary TEXT,
            engagement_score INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            first_posted TIMESTAMP,
            last_edited TIMESTAMP,
            last_comment_at TIMESTAMP,
            last_checked_at TIMESTAMP,
            scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT,
            content TEXT,
            published_date TIMESTAMP,
            sentiment TEXT,
            primary_topic TEXT,
            topics TEXT,
            included_in_feed BOOLEAN
        );

        CREATE TABLE feature_announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_id TEXT,
            option_id TEXT,
            content_id TEXT NOT NULL,
            h4_title TEXT NOT NULL,
            anchor_id TEXT,
            section TEXT,
            category TEXT,
            raw_content TEXT,
            summary TEXT,
            description TEXT,
            implications TEXT,
            enable_location_account TEXT,
            enable_location_course TEXT,
            subaccount_config BOOLEAN,
            account_course_setting TEXT,
            permissions TEXT,
            affected_areas TEXT,
            affects_ui BOOLEAN,
            added_date DATE,
            announced_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (feature_id) REFERENCES features(feature_id),
            FOREIGN KEY (option_id) REFERENCES feature_options(option_id),
            FOREIGN KEY (content_id) REFERENCES content_items(source_id)
        );

        CREATE TABLE content_feature_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id TEXT NOT NULL,
            feature_id TEXT,
            option_id TEXT,
            mention_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES content_items(source_id),
            FOREIGN KEY (feature_id) REFERENCES features(feature_id),
            FOREIGN KEY (option_id) REFERENCES feature_options(option_id)
        );

        CREATE TABLE upcoming_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id TEXT NOT NULL,
            change_date DATE NOT NULL,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES content_items(source_id)
        );
    """)
    conn.commit()
    conn.close()

    # Patch database path
    original_path = database.DB_PATH
    database.DB_PATH = db_path

    yield db_path

    # Restore original path
    database.DB_PATH = original_path


@pytest.fixture
def client(test_db):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def populated_db(test_db):
    """Create a test database with sample data."""
    conn = sqlite3.connect(test_db)

    # Insert sample features
    conn.executescript("""
        INSERT INTO features (feature_id, name, description, status)
        VALUES
            ('assignments', 'Assignments', 'Create and manage assignments', 'active'),
            ('gradebook', 'Gradebook', 'View and manage grades', 'active'),
            ('speedgrader', 'SpeedGrader', 'Grade submissions quickly', 'active');

        INSERT INTO feature_options (option_id, feature_id, canonical_name, name, status, beta_date, production_date, description, meta_summary)
        VALUES
            ('document_processor', 'assignments', 'Document Processor', 'Document Processing App', 'preview', '2026-03-01', '2026-03-15', 'Enables document annotation', 'Feature is in preview. Available in beta March 1.'),
            ('enhanced_filters', 'gradebook', 'Enhanced Gradebook Filters', 'Enhanced Filters', 'optional', NULL, '2026-01-15', 'Additional filtering options', 'Feature is available and optional.'),
            ('speedgrader_sort', 'speedgrader', 'Sort by Student Name', 'Sort by Name', 'released', NULL, '2025-12-01', 'Sort submissions alphabetically', 'Feature is fully released.');

        INSERT INTO content_items (source_id, url, title, content_type, summary, first_posted, published_date)
        VALUES
            ('release_note_2026-02-21', 'https://community.instructure.com/release-2026-02-21', 'Canvas Release Notes (2026-02-21)', 'release_note', 'February release with new features', '2026-02-21 00:00:00', '2026-02-21 00:00:00'),
            ('deploy_note_2026-02-18', 'https://community.instructure.com/deploy-2026-02-18', 'Canvas Deploy Notes (2026-02-18)', 'deploy_note', 'Bug fixes and improvements', '2026-02-18 00:00:00', '2026-02-18 00:00:00'),
            ('blog_12345', 'https://community.instructure.com/blog/12345', 'February Product Updates', 'blog', 'Monthly product update summary', '2026-02-15 00:00:00', '2026-02-15 00:00:00'),
            ('question_67890', 'https://community.instructure.com/qa/67890', 'SpeedGrader not loading', 'question', 'User reports loading issues', '2026-02-10 00:00:00', '2026-02-10 00:00:00');

        INSERT INTO feature_announcements (feature_id, option_id, content_id, h4_title, section, category, description, implications, announced_at)
        VALUES
            ('assignments', 'document_processor', 'release_note_2026-02-21', 'Document Processing App', 'New Features', 'Assignments', 'New document annotation feature', 'Admins should evaluate for rollout', '2026-02-21 00:00:00'),
            ('gradebook', 'enhanced_filters', 'release_note_2026-02-21', 'Enhanced Gradebook Filters', 'Updated Features', 'Gradebook', 'Additional filter options', 'May help instructors manage large courses', '2026-02-21 00:00:00');

        INSERT INTO content_feature_refs (content_id, feature_id, option_id, mention_type)
        VALUES
            ('question_67890', 'speedgrader', NULL, 'questions'),
            ('blog_12345', 'assignments', 'document_processor', 'discusses');

        INSERT INTO upcoming_changes (content_id, change_date, description)
        VALUES
            ('release_note_2026-02-21', '2026-03-21', 'User-Agent Header Enforcement'),
            ('release_note_2026-02-21', '2026-04-18', 'CDN Infrastructure Changes');
    """)
    conn.commit()
    conn.close()

    return test_db
```

**Step 3: Create health check test**

```python
# tests/test_api/test_health.py
"""Tests for health check endpoint."""


def test_health_check(client):
    """Test health check returns healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
```

**Step 4: Run test to verify it passes**

```bash
cd .worktrees/feature-tracker
pytest tests/test_api/test_health.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_api/
git commit -m "test(api): add test infrastructure and health check test"
```

---

### Task 1.3: Implement Dashboard API Endpoint

**Files:**
- Create: `src/api/routes/__init__.py`
- Create: `src/api/routes/dashboard.py`
- Create: `tests/test_api/test_dashboard.py`
- Modify: `src/api/main.py`

**Step 1: Write the failing test**

```python
# tests/test_api/test_dashboard.py
"""Tests for dashboard API endpoint."""
import pytest


def test_dashboard_returns_current_data(client, populated_db):
    """Test dashboard returns current release/deploy notes and activity."""
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()

    # Should have all dashboard sections
    assert "release_note" in data
    assert "deploy_note" in data
    assert "upcoming_changes" in data
    assert "recent_activity" in data

    # Release note should be the most recent
    assert data["release_note"]["title"] == "Canvas Release Notes (2026-02-21)"

    # Deploy note should be present
    assert data["deploy_note"]["title"] == "Canvas Deploy Notes (2026-02-18)"

    # Should have upcoming changes
    assert len(data["upcoming_changes"]) == 2

    # Should have recent activity (blog + Q&A)
    assert len(data["recent_activity"]) >= 2


def test_dashboard_with_date_filter(client, populated_db):
    """Test dashboard can filter by specific publish date."""
    response = client.get("/api/dashboard?date=2026-02-21")
    assert response.status_code == 200
    data = response.json()

    # Should return release note for that date
    assert data["release_note"]["title"] == "Canvas Release Notes (2026-02-21)"


def test_dashboard_with_invalid_date(client, populated_db):
    """Test dashboard with date that has no content."""
    response = client.get("/api/dashboard?date=2020-01-01")
    assert response.status_code == 200
    data = response.json()

    # Should return empty/null for missing content
    assert data["release_note"] is None


def test_dashboard_upcoming_changes_sorted_by_date(client, populated_db):
    """Test upcoming changes are sorted by date ascending."""
    response = client.get("/api/dashboard")
    data = response.json()

    changes = data["upcoming_changes"]
    dates = [c["change_date"] for c in changes]
    assert dates == sorted(dates)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_api/test_dashboard.py -v
```

Expected: FAIL (404 - endpoint doesn't exist)

**Step 3: Create routes package**

```python
# src/api/routes/__init__.py
"""API routes package."""
```

**Step 4: Implement dashboard route**

```python
# src/api/routes/dashboard.py
"""Dashboard API endpoint."""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import date

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(date: Optional[str] = Query(None, description="Filter by publish date (YYYY-MM-DD)")):
    """
    Get dashboard data including current release/deploy notes,
    upcoming changes, and recent activity.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get release note (most recent or by date)
        if date:
            cursor.execute("""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'release_note'
                AND date(first_posted) = ?
                ORDER BY first_posted DESC
                LIMIT 1
            """, (date,))
        else:
            cursor.execute("""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'release_note'
                ORDER BY first_posted DESC
                LIMIT 1
            """)
        release_note = row_to_dict(cursor.fetchone())

        # Get deploy note (most recent or by date)
        if date:
            cursor.execute("""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'deploy_note'
                AND date(first_posted) = ?
                ORDER BY first_posted DESC
                LIMIT 1
            """, (date,))
        else:
            cursor.execute("""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'deploy_note'
                ORDER BY first_posted DESC
                LIMIT 1
            """)
        deploy_note = row_to_dict(cursor.fetchone())

        # Get upcoming changes (from most recent release note)
        upcoming_changes = []
        if release_note:
            cursor.execute("""
                SELECT change_date, description
                FROM upcoming_changes
                WHERE content_id = ?
                ORDER BY change_date ASC
            """, (release_note["source_id"],))
            upcoming_changes = rows_to_list(cursor.fetchall())

        # Get recent activity (blog + Q&A posts, last 7 days)
        cursor.execute("""
            SELECT source_id, url, title, content_type, summary, first_posted
            FROM content_items
            WHERE content_type IN ('blog', 'question')
            ORDER BY first_posted DESC
            LIMIT 10
        """)
        recent_activity = rows_to_list(cursor.fetchall())

        # Get feature announcements for release note
        announcements = []
        if release_note:
            cursor.execute("""
                SELECT
                    fa.h4_title,
                    fa.section,
                    fa.category,
                    fa.description,
                    fa.option_id,
                    fo.beta_date,
                    fo.production_date,
                    fo.status as option_status
                FROM feature_announcements fa
                LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
                WHERE fa.content_id = ?
                ORDER BY fa.section, fa.category
            """, (release_note["source_id"],))
            announcements = rows_to_list(cursor.fetchall())

        if release_note:
            release_note["announcements"] = announcements

        return {
            "release_note": release_note,
            "deploy_note": deploy_note,
            "upcoming_changes": upcoming_changes,
            "recent_activity": recent_activity,
        }
```

**Step 5: Register route in main app**

```python
# src/api/main.py (updated)
"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from src.api.routes import dashboard

app = FastAPI(
    title="Canvas Feature Tracker API",
    description="API for tracking Canvas LMS feature options and deployment readiness",
    version="1.0.0",
)

# Register routers
app.include_router(dashboard.router)

# Static files will be mounted after frontend build exists
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}
```

**Step 6: Run tests to verify they pass**

```bash
pytest tests/test_api/test_dashboard.py -v
```

Expected: PASS (4 tests)

**Step 7: Commit**

```bash
git add src/api/ tests/test_api/
git commit -m "feat(api): implement dashboard endpoint with date filtering"
```

---

### Task 1.4: Implement Features API Endpoint

**Files:**
- Create: `src/api/routes/features.py`
- Create: `tests/test_api/test_features.py`
- Modify: `src/api/main.py`

**Step 1: Write the failing test**

```python
# tests/test_api/test_features.py
"""Tests for features API endpoint."""
import pytest


def test_get_features_list(client, populated_db):
    """Test getting list of all features with option counts."""
    response = client.get("/api/features")
    assert response.status_code == 200
    data = response.json()

    assert "features" in data
    assert len(data["features"]) == 3  # assignments, gradebook, speedgrader

    # Each feature should have counts
    assignments = next(f for f in data["features"] if f["feature_id"] == "assignments")
    assert assignments["name"] == "Assignments"
    assert assignments["option_count"] >= 1
    assert "status_summary" in assignments


def test_get_features_with_category_filter(client, populated_db):
    """Test filtering features by category."""
    response = client.get("/api/features?category=grading")
    assert response.status_code == 200
    # Category filter would need category data in fixtures


def test_get_feature_detail(client, populated_db):
    """Test getting a single feature with its options."""
    response = client.get("/api/features/assignments")
    assert response.status_code == 200
    data = response.json()

    assert data["feature_id"] == "assignments"
    assert data["name"] == "Assignments"
    assert "options" in data
    assert len(data["options"]) >= 1
    assert "announcements" in data
    assert "community_posts" in data


def test_get_feature_detail_not_found(client, populated_db):
    """Test 404 for non-existent feature."""
    response = client.get("/api/features/nonexistent")
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_api/test_features.py -v
```

Expected: FAIL (404 - endpoint doesn't exist)

**Step 3: Implement features route**

```python
# src/api/routes/features.py
"""Features API endpoint."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["features"])


# Category mapping for filtering
FEATURE_CATEGORIES = {
    "core": ["announcements", "assignments", "discussions", "files", "modules", "pages", "syllabus"],
    "grading": ["gradebook", "speedgrader", "rubrics", "outcomes", "mastery_paths", "peer_reviews", "roll_call_attendance"],
    "quizzes": ["classic_quizzes", "new_quizzes"],
    "collaboration": ["collaborations", "conferences", "groups", "chat"],
    "communication": ["inbox", "calendar", "notifications"],
    "ui": ["dashboard", "global_navigation", "profile_settings", "rich_content_editor"],
    "portfolio": ["eportfolios", "student_eportfolios"],
    "analytics": ["canvas_analytics", "canvas_data_services"],
    "addons": ["canvas_catalog", "canvas_studio", "canvas_commons", "student_pathways", "mastery_connect", "parchment_badges"],
    "mobile": ["canvas_mobile"],
    "admin": ["course_import", "blueprint_courses", "sis_import", "external_apps_lti", "canvas_apps", "developer_keys", "reports", "api", "account_settings", "themes_branding", "authentication"],
}


@router.get("/features")
def get_features(category: Optional[str] = Query(None, description="Filter by category")):
    """Get list of all features with option counts and status summary."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Build query with optional category filter
        query = """
            SELECT
                f.feature_id,
                f.name,
                f.description,
                f.status,
                COUNT(fo.option_id) as option_count,
                SUM(CASE WHEN fo.status = 'preview' THEN 1 ELSE 0 END) as preview_count,
                SUM(CASE WHEN fo.status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN fo.status = 'optional' THEN 1 ELSE 0 END) as optional_count
            FROM features f
            LEFT JOIN feature_options fo ON f.feature_id = fo.feature_id
        """

        params = []
        if category and category in FEATURE_CATEGORIES:
            placeholders = ",".join("?" * len(FEATURE_CATEGORIES[category]))
            query += f" WHERE f.feature_id IN ({placeholders})"
            params = FEATURE_CATEGORIES[category]

        query += " GROUP BY f.feature_id ORDER BY f.name"

        cursor.execute(query, params)
        features = rows_to_list(cursor.fetchall())

        # Add status summary to each feature
        for feature in features:
            summaries = []
            if feature["preview_count"]:
                summaries.append(f"{feature['preview_count']} in preview")
            if feature["pending_count"]:
                summaries.append(f"{feature['pending_count']} pending")
            if feature["optional_count"]:
                summaries.append(f"{feature['optional_count']} optional")
            if not summaries and feature["option_count"]:
                summaries.append("all stable")
            feature["status_summary"] = ", ".join(summaries) if summaries else ""

        return {"features": features}


@router.get("/features/{feature_id}")
def get_feature_detail(feature_id: str):
    """Get detailed information about a specific feature."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get feature
        cursor.execute("""
            SELECT feature_id, name, description, status
            FROM features
            WHERE feature_id = ?
        """, (feature_id,))
        feature = row_to_dict(cursor.fetchone())

        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")

        # Get associated options
        cursor.execute("""
            SELECT
                option_id, canonical_name, name, description, meta_summary,
                status, beta_date, production_date, deprecation_date,
                config_level, default_state, user_group_url,
                first_seen, last_seen
            FROM feature_options
            WHERE feature_id = ?
            ORDER BY name
        """, (feature_id,))
        feature["options"] = rows_to_list(cursor.fetchall())

        # Get recent announcements
        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.section, fa.category,
                fa.description, fa.announced_at,
                ci.title as release_title, ci.url as release_url
            FROM feature_announcements fa
            JOIN content_items ci ON fa.content_id = ci.source_id
            WHERE fa.feature_id = ?
            ORDER BY fa.announced_at DESC
            LIMIT 10
        """, (feature_id,))
        feature["announcements"] = rows_to_list(cursor.fetchall())

        # Get related community posts
        cursor.execute("""
            SELECT
                ci.source_id, ci.url, ci.title, ci.content_type,
                ci.summary, ci.first_posted,
                cfr.mention_type
            FROM content_feature_refs cfr
            JOIN content_items ci ON cfr.content_id = ci.source_id
            WHERE cfr.feature_id = ?
            AND ci.content_type IN ('blog', 'question')
            ORDER BY ci.first_posted DESC
            LIMIT 10
        """, (feature_id,))
        feature["community_posts"] = rows_to_list(cursor.fetchall())

        return feature
```

**Step 4: Register route in main app**

Add to `src/api/main.py`:

```python
from src.api.routes import dashboard, features

# Register routers
app.include_router(dashboard.router)
app.include_router(features.router)
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_api/test_features.py -v
```

Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add src/api/ tests/test_api/
git commit -m "feat(api): implement features endpoint with detail view"
```

---

### Task 1.5: Implement Options API Endpoint

**Files:**
- Create: `src/api/routes/options.py`
- Create: `tests/test_api/test_options.py`
- Modify: `src/api/main.py`

**Step 1: Write the failing test**

```python
# tests/test_api/test_options.py
"""Tests for options API endpoint."""
import pytest


def test_get_options_list(client, populated_db):
    """Test getting list of all feature options."""
    response = client.get("/api/options")
    assert response.status_code == 200
    data = response.json()

    assert "options" in data
    assert len(data["options"]) == 3  # document_processor, enhanced_filters, speedgrader_sort

    # Each option should have feature info
    doc_processor = next(o for o in data["options"] if o["option_id"] == "document_processor")
    assert doc_processor["feature_id"] == "assignments"
    assert doc_processor["status"] == "preview"


def test_get_options_filtered_by_status(client, populated_db):
    """Test filtering options by status."""
    response = client.get("/api/options?status=preview")
    assert response.status_code == 200
    data = response.json()

    assert len(data["options"]) == 1
    assert data["options"][0]["option_id"] == "document_processor"


def test_get_options_filtered_by_feature(client, populated_db):
    """Test filtering options by feature."""
    response = client.get("/api/options?feature=gradebook")
    assert response.status_code == 200
    data = response.json()

    assert len(data["options"]) == 1
    assert data["options"][0]["option_id"] == "enhanced_filters"


def test_get_options_sorted_by_beta_date(client, populated_db):
    """Test sorting options by beta date."""
    response = client.get("/api/options?sort=beta_date")
    assert response.status_code == 200
    data = response.json()

    # document_processor has beta_date, should be first among those with dates
    assert "options" in data


def test_get_option_detail(client, populated_db):
    """Test getting a single option with full details."""
    response = client.get("/api/options/document_processor")
    assert response.status_code == 200
    data = response.json()

    assert data["option_id"] == "document_processor"
    assert data["canonical_name"] == "Document Processor"
    assert data["feature"]["feature_id"] == "assignments"
    assert "announcements" in data
    assert "community_posts" in data
    assert "configuration" in data


def test_get_option_detail_not_found(client, populated_db):
    """Test 404 for non-existent option."""
    response = client.get("/api/options/nonexistent")
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_api/test_options.py -v
```

Expected: FAIL (404 - endpoint doesn't exist)

**Step 3: Implement options route**

```python
# src/api/routes/options.py
"""Options API endpoint."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Literal

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["options"])


@router.get("/options")
def get_options(
    status: Optional[str] = Query(None, description="Filter by status (pending, preview, optional, default_optional, released)"),
    feature: Optional[str] = Query(None, description="Filter by feature_id"),
    sort: Optional[Literal["updated", "alphabetical", "beta_date", "production_date"]] = Query("updated", description="Sort order"),
):
    """Get list of all feature options with filtering and sorting."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Build query
        query = """
            SELECT
                fo.option_id,
                fo.feature_id,
                fo.canonical_name,
                fo.name,
                fo.description,
                fo.status,
                fo.beta_date,
                fo.production_date,
                fo.deprecation_date,
                fo.last_updated,
                f.name as feature_name
            FROM feature_options fo
            JOIN features f ON fo.feature_id = f.feature_id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND fo.status = ?"
            params.append(status)

        if feature:
            query += " AND fo.feature_id = ?"
            params.append(feature)

        # Sort order
        if sort == "alphabetical":
            query += " ORDER BY fo.name"
        elif sort == "beta_date":
            query += " ORDER BY fo.beta_date IS NULL, fo.beta_date ASC, fo.name"
        elif sort == "production_date":
            query += " ORDER BY fo.production_date IS NULL, fo.production_date ASC, fo.name"
        else:  # updated (default)
            query += " ORDER BY fo.last_updated DESC NULLS LAST, fo.name"

        cursor.execute(query, params)
        options = rows_to_list(cursor.fetchall())

        return {"options": options}


@router.get("/options/{option_id}")
def get_option_detail(option_id: str):
    """Get detailed information about a specific feature option."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get option
        cursor.execute("""
            SELECT
                fo.*,
                f.name as feature_name,
                f.description as feature_description
            FROM feature_options fo
            JOIN features f ON fo.feature_id = f.feature_id
            WHERE fo.option_id = ?
        """, (option_id,))
        option = row_to_dict(cursor.fetchone())

        if not option:
            raise HTTPException(status_code=404, detail="Feature option not found")

        # Structure the response
        result = {
            "option_id": option["option_id"],
            "canonical_name": option["canonical_name"],
            "name": option["name"],
            "description": option["description"],
            "meta_summary": option["meta_summary"],
            "status": option["status"],
            "beta_date": option["beta_date"],
            "production_date": option["production_date"],
            "deprecation_date": option["deprecation_date"],
            "first_seen": option["first_seen"],
            "last_seen": option["last_seen"],
            "user_group_url": option["user_group_url"],
            "feature": {
                "feature_id": option["feature_id"],
                "name": option["feature_name"],
                "description": option["feature_description"],
            },
            "configuration": {
                "config_level": option["config_level"],
                "default_state": option["default_state"],
            },
        }

        # Get announcements
        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.section, fa.category,
                fa.description, fa.implications, fa.announced_at,
                fa.enable_location_account, fa.enable_location_course,
                fa.subaccount_config, fa.permissions, fa.affected_areas,
                fa.affects_ui,
                ci.title as release_title, ci.url as release_url
            FROM feature_announcements fa
            JOIN content_items ci ON fa.content_id = ci.source_id
            WHERE fa.option_id = ?
            ORDER BY fa.announced_at DESC
        """, (option_id,))
        result["announcements"] = rows_to_list(cursor.fetchall())

        # Get configuration from most recent announcement
        if result["announcements"]:
            latest = result["announcements"][0]
            result["configuration"].update({
                "enable_location_account": latest["enable_location_account"],
                "enable_location_course": latest["enable_location_course"],
                "subaccount_config": latest["subaccount_config"],
                "permissions": latest["permissions"],
                "affected_areas": latest["affected_areas"],
                "affects_ui": latest["affects_ui"],
            })

        # Get community posts
        cursor.execute("""
            SELECT
                ci.source_id, ci.url, ci.title, ci.content_type,
                ci.summary, ci.first_posted,
                cfr.mention_type
            FROM content_feature_refs cfr
            JOIN content_items ci ON cfr.content_id = ci.source_id
            WHERE cfr.option_id = ?
            AND ci.content_type IN ('blog', 'question')
            ORDER BY ci.first_posted DESC
            LIMIT 10
        """, (option_id,))
        result["community_posts"] = rows_to_list(cursor.fetchall())

        return result
```

**Step 4: Register route in main app**

Add to `src/api/main.py`:

```python
from src.api.routes import dashboard, features, options

# Register routers
app.include_router(dashboard.router)
app.include_router(features.router)
app.include_router(options.router)
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_api/test_options.py -v
```

Expected: PASS (6 tests)

**Step 6: Commit**

```bash
git add src/api/ tests/test_api/
git commit -m "feat(api): implement options endpoint with filtering and detail view"
```

---

### Task 1.6: Implement Releases Archive API Endpoint

**Files:**
- Create: `src/api/routes/releases.py`
- Create: `tests/test_api/test_releases.py`
- Modify: `src/api/main.py`

**Step 1: Write the failing test**

```python
# tests/test_api/test_releases.py
"""Tests for releases archive API endpoint."""
import pytest


def test_get_releases_list(client, populated_db):
    """Test getting list of release/deploy notes."""
    response = client.get("/api/releases")
    assert response.status_code == 200
    data = response.json()

    assert "releases" in data
    # Should have release_note and deploy_note
    types = [r["content_type"] for r in data["releases"]]
    assert "release_note" in types
    assert "deploy_note" in types


def test_get_releases_filtered_by_type(client, populated_db):
    """Test filtering releases by type."""
    response = client.get("/api/releases?type=release_note")
    assert response.status_code == 200
    data = response.json()

    for release in data["releases"]:
        assert release["content_type"] == "release_note"


def test_get_releases_filtered_by_year(client, populated_db):
    """Test filtering releases by year."""
    response = client.get("/api/releases?year=2026")
    assert response.status_code == 200
    data = response.json()

    for release in data["releases"]:
        assert "2026" in release["first_posted"]


def test_get_release_detail(client, populated_db):
    """Test getting full release note content."""
    response = client.get("/api/releases/release_note_2026-02-21")
    assert response.status_code == 200
    data = response.json()

    assert data["source_id"] == "release_note_2026-02-21"
    assert data["title"] == "Canvas Release Notes (2026-02-21)"
    assert "announcements" in data
    assert "upcoming_changes" in data


def test_get_release_detail_not_found(client, populated_db):
    """Test 404 for non-existent release."""
    response = client.get("/api/releases/nonexistent")
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_api/test_releases.py -v
```

Expected: FAIL (404 - endpoint doesn't exist)

**Step 3: Implement releases route**

```python
# src/api/routes/releases.py
"""Releases archive API endpoint."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["releases"])


@router.get("/releases")
def get_releases(
    type: Optional[str] = Query(None, description="Filter by type (release_note, deploy_note)"),
    year: Optional[int] = Query(None, description="Filter by year"),
    search: Optional[str] = Query(None, description="Search in title"),
):
    """Get list of release and deploy notes."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
                ci.source_id,
                ci.url,
                ci.title,
                ci.content_type,
                ci.summary,
                ci.first_posted,
                COUNT(fa.id) as announcement_count
            FROM content_items ci
            LEFT JOIN feature_announcements fa ON ci.source_id = fa.content_id
            WHERE ci.content_type IN ('release_note', 'deploy_note')
        """
        params = []

        if type:
            query += " AND ci.content_type = ?"
            params.append(type)

        if year:
            query += " AND strftime('%Y', ci.first_posted) = ?"
            params.append(str(year))

        if search:
            query += " AND ci.title LIKE ?"
            params.append(f"%{search}%")

        query += " GROUP BY ci.source_id ORDER BY ci.first_posted DESC"

        cursor.execute(query, params)
        releases = rows_to_list(cursor.fetchall())

        return {"releases": releases}


@router.get("/releases/{content_id}")
def get_release_detail(content_id: str):
    """Get full release or deploy note with all announcements."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get release/deploy note
        cursor.execute("""
            SELECT source_id, url, title, content_type, summary, first_posted
            FROM content_items
            WHERE source_id = ?
            AND content_type IN ('release_note', 'deploy_note')
        """, (content_id,))
        release = row_to_dict(cursor.fetchone())

        if not release:
            raise HTTPException(status_code=404, detail="Release not found")

        # Get announcements grouped by section
        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.anchor_id, fa.section, fa.category,
                fa.description, fa.implications, fa.option_id,
                fa.enable_location_account, fa.enable_location_course,
                fo.beta_date, fo.production_date, fo.status as option_status
            FROM feature_announcements fa
            LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
            WHERE fa.content_id = ?
            ORDER BY fa.section, fa.category, fa.h4_title
        """, (content_id,))
        release["announcements"] = rows_to_list(cursor.fetchall())

        # Get upcoming changes
        cursor.execute("""
            SELECT change_date, description
            FROM upcoming_changes
            WHERE content_id = ?
            ORDER BY change_date ASC
        """, (content_id,))
        release["upcoming_changes"] = rows_to_list(cursor.fetchall())

        return release
```

**Step 4: Register route in main app**

Add to `src/api/main.py`:

```python
from src.api.routes import dashboard, features, options, releases

# Register routers
app.include_router(dashboard.router)
app.include_router(features.router)
app.include_router(options.router)
app.include_router(releases.router)
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_api/test_releases.py -v
```

Expected: PASS (5 tests)

**Step 6: Commit**

```bash
git add src/api/ tests/test_api/
git commit -m "feat(api): implement releases archive endpoint"
```

---

### Task 1.7: Implement Search API Endpoint

**Files:**
- Create: `src/api/routes/search.py`
- Create: `tests/test_api/test_search.py`
- Modify: `src/api/main.py`

**Step 1: Write the failing test**

```python
# tests/test_api/test_search.py
"""Tests for search API endpoint."""
import pytest


def test_search_returns_results(client, populated_db):
    """Test search returns matching results."""
    response = client.get("/api/search?q=document")
    assert response.status_code == 200
    data = response.json()

    assert "features" in data
    assert "options" in data
    assert "content" in data

    # Should find document_processor option
    assert len(data["options"]) >= 1


def test_search_features(client, populated_db):
    """Test search finds features by name."""
    response = client.get("/api/search?q=assignments")
    data = response.json()

    assert len(data["features"]) >= 1
    assert data["features"][0]["feature_id"] == "assignments"


def test_search_empty_query(client, populated_db):
    """Test search with empty query returns empty results."""
    response = client.get("/api/search?q=")
    assert response.status_code == 200
    data = response.json()

    assert data["features"] == []
    assert data["options"] == []
    assert data["content"] == []


def test_search_no_results(client, populated_db):
    """Test search with no matches."""
    response = client.get("/api/search?q=xyznonexistent")
    assert response.status_code == 200
    data = response.json()

    assert data["features"] == []
    assert data["options"] == []
    assert data["content"] == []
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_api/test_search.py -v
```

Expected: FAIL (404 - endpoint doesn't exist)

**Step 3: Implement search route**

```python
# src/api/routes/search.py
"""Search API endpoint."""
from fastapi import APIRouter, Query

from src.api.database import get_db, rows_to_list

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def search(q: str = Query("", description="Search query")):
    """Search across features, options, and content."""
    if not q or len(q.strip()) < 2:
        return {"features": [], "options": [], "content": []}

    search_term = f"%{q}%"

    with get_db() as conn:
        cursor = conn.cursor()

        # Search features
        cursor.execute("""
            SELECT feature_id, name, description, status
            FROM features
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY name
            LIMIT 10
        """, (search_term, search_term))
        features = rows_to_list(cursor.fetchall())

        # Search options
        cursor.execute("""
            SELECT
                fo.option_id, fo.canonical_name, fo.name, fo.description,
                fo.status, fo.feature_id,
                f.name as feature_name
            FROM feature_options fo
            JOIN features f ON fo.feature_id = f.feature_id
            WHERE fo.name LIKE ? OR fo.canonical_name LIKE ? OR fo.description LIKE ?
            ORDER BY fo.name
            LIMIT 10
        """, (search_term, search_term, search_term))
        options = rows_to_list(cursor.fetchall())

        # Search content (release notes, blogs, Q&A)
        cursor.execute("""
            SELECT source_id, url, title, content_type, summary, first_posted
            FROM content_items
            WHERE title LIKE ? OR summary LIKE ?
            ORDER BY first_posted DESC
            LIMIT 10
        """, (search_term, search_term))
        content = rows_to_list(cursor.fetchall())

        return {
            "features": features,
            "options": options,
            "content": content,
        }
```

**Step 4: Register route in main app**

Add to `src/api/main.py`:

```python
from src.api.routes import dashboard, features, options, releases, search

# Register routers
app.include_router(dashboard.router)
app.include_router(features.router)
app.include_router(options.router)
app.include_router(releases.router)
app.include_router(search.router)
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_api/test_search.py -v
```

Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add src/api/ tests/test_api/
git commit -m "feat(api): implement global search endpoint"
```

---

### Task 1.8: Run All API Tests

**Step 1: Run full API test suite**

```bash
pytest tests/test_api/ -v
```

Expected: All tests pass (24+ tests)

**Step 2: Commit completion marker**

```bash
git commit --allow-empty -m "milestone: Phase 1 complete - API endpoints implemented"
```

---

## Phase 2: Frontend Scaffolding

### Task 2.1: Initialize React Project with Vite

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`

**Step 1: Create frontend directory and initialize**

```bash
cd .worktrees/feature-tracker
mkdir frontend
cd frontend
npm create vite@latest . -- --template react-ts
```

Select: React, TypeScript

**Step 2: Install dependencies**

```bash
npm install
npm install react-router-dom @tanstack/react-query axios
npm install -D tailwindcss postcss autoprefixer @types/react-router-dom
npx tailwindcss init -p
```

**Step 3: Configure Tailwind**

Update `frontend/tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Canvas-inspired color palette
        canvas: {
          primary: '#0374B5',
          secondary: '#394B58',
          success: '#0B874B',
          warning: '#BF4D00',
          danger: '#D64242',
          light: '#F5F5F5',
        }
      }
    },
  },
  plugins: [],
}
```

**Step 4: Add Tailwind to CSS**

Update `frontend/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-gray-50 text-gray-900;
}
```

**Step 5: Configure Vite proxy for API**

Update `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 6: Verify setup**

```bash
npm run dev
```

Should start dev server on http://localhost:5173

**Step 7: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): initialize Vite + React + TypeScript + Tailwind"
```

---

### Task 2.2: Create TypeScript Types

**Files:**
- Create: `frontend/src/types/index.ts`

**Step 1: Create type definitions**

```typescript
// frontend/src/types/index.ts

export interface Feature {
  feature_id: string;
  name: string;
  description: string | null;
  status: string;
  option_count?: number;
  preview_count?: number;
  pending_count?: number;
  optional_count?: number;
  status_summary?: string;
}

export interface FeatureOption {
  option_id: string;
  feature_id: string;
  canonical_name: string | null;
  name: string;
  description: string | null;
  meta_summary: string | null;
  status: string;
  beta_date: string | null;
  production_date: string | null;
  deprecation_date: string | null;
  config_level: string | null;
  default_state: string | null;
  user_group_url: string | null;
  first_seen: string | null;
  last_seen: string | null;
  feature_name?: string;
}

export interface FeatureOptionDetail extends FeatureOption {
  feature: {
    feature_id: string;
    name: string;
    description: string | null;
  };
  configuration: {
    config_level: string | null;
    default_state: string | null;
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

export interface Announcement {
  id: number;
  h4_title: string;
  section: string | null;
  category: string | null;
  description: string | null;
  implications: string | null;
  announced_at: string;
  release_title?: string;
  release_url?: string;
  option_id?: string;
  beta_date?: string | null;
  production_date?: string | null;
  option_status?: string;
  enable_location_account?: string | null;
  enable_location_course?: string | null;
  subaccount_config?: boolean | null;
  permissions?: string | null;
  affected_areas?: string | null;
  affects_ui?: boolean | null;
}

export interface CommunityPost {
  source_id: string;
  url: string;
  title: string;
  content_type: string;
  summary: string | null;
  first_posted: string;
  mention_type?: string;
}

export interface Release {
  source_id: string;
  url: string;
  title: string;
  content_type: string;
  summary: string | null;
  first_posted: string;
  announcement_count?: number;
  announcements?: Announcement[];
  upcoming_changes?: UpcomingChange[];
}

export interface UpcomingChange {
  change_date: string;
  description: string;
}

export interface DashboardData {
  release_note: Release | null;
  deploy_note: Release | null;
  upcoming_changes: UpcomingChange[];
  recent_activity: CommunityPost[];
}

export interface SearchResults {
  features: Feature[];
  options: FeatureOption[];
  content: CommunityPost[];
}
```

**Step 2: Commit**

```bash
git add frontend/src/types/
git commit -m "feat(frontend): add TypeScript type definitions"
```

---

### Task 2.3: Create API Client

**Files:**
- Create: `frontend/src/api/client.ts`

**Step 1: Create API client**

```typescript
// frontend/src/api/client.ts
import axios from 'axios';
import type {
  DashboardData,
  Feature,
  FeatureOption,
  FeatureOptionDetail,
  Release,
  SearchResults,
} from '../types';

const api = axios.create({
  baseURL: '/api',
});

export const dashboardApi = {
  get: async (date?: string): Promise<DashboardData> => {
    const params = date ? { date } : {};
    const { data } = await api.get('/dashboard', { params });
    return data;
  },
};

export const featuresApi = {
  list: async (category?: string): Promise<{ features: Feature[] }> => {
    const params = category ? { category } : {};
    const { data } = await api.get('/features', { params });
    return data;
  },
  get: async (featureId: string): Promise<Feature & { options: FeatureOption[]; announcements: Announcement[]; community_posts: CommunityPost[] }> => {
    const { data } = await api.get(`/features/${featureId}`);
    return data;
  },
};

export const optionsApi = {
  list: async (params?: {
    status?: string;
    feature?: string;
    sort?: string;
  }): Promise<{ options: FeatureOption[] }> => {
    const { data } = await api.get('/options', { params });
    return data;
  },
  get: async (optionId: string): Promise<FeatureOptionDetail> => {
    const { data } = await api.get(`/options/${optionId}`);
    return data;
  },
};

export const releasesApi = {
  list: async (params?: {
    type?: string;
    year?: number;
    search?: string;
  }): Promise<{ releases: Release[] }> => {
    const { data } = await api.get('/releases', { params });
    return data;
  },
  get: async (contentId: string): Promise<Release> => {
    const { data } = await api.get(`/releases/${contentId}`);
    return data;
  },
};

export const searchApi = {
  search: async (q: string): Promise<SearchResults> => {
    const { data } = await api.get('/search', { params: { q } });
    return data;
  },
};
```

**Step 2: Commit**

```bash
git add frontend/src/api/
git commit -m "feat(frontend): add API client with typed endpoints"
```

---

### Task 2.4: Set Up React Router

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

**Step 1: Update main.tsx with React Query**

```typescript
// frontend/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
```

**Step 2: Update App.tsx with routes**

```typescript
// frontend/src/App.tsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Features from './pages/Features'
import FeatureDetail from './pages/FeatureDetail'
import Options from './pages/Options'
import OptionDetail from './pages/OptionDetail'
import Releases from './pages/Releases'
import ReleaseDetail from './pages/ReleaseDetail'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="features" element={<Features />} />
        <Route path="features/:featureId" element={<FeatureDetail />} />
        <Route path="options" element={<Options />} />
        <Route path="options/:optionId" element={<OptionDetail />} />
        <Route path="releases" element={<Releases />} />
        <Route path="releases/:contentId" element={<ReleaseDetail />} />
      </Route>
    </Routes>
  )
}

export default App
```

**Step 3: Create placeholder pages**

Create minimal placeholder files for each page (will be implemented in Phase 3):

```typescript
// frontend/src/pages/Dashboard.tsx
export default function Dashboard() {
  return <div>Dashboard - Coming soon</div>
}

// frontend/src/pages/Features.tsx
export default function Features() {
  return <div>Features - Coming soon</div>
}

// frontend/src/pages/FeatureDetail.tsx
export default function FeatureDetail() {
  return <div>Feature Detail - Coming soon</div>
}

// frontend/src/pages/Options.tsx
export default function Options() {
  return <div>Options - Coming soon</div>
}

// frontend/src/pages/OptionDetail.tsx
export default function OptionDetail() {
  return <div>Option Detail - Coming soon</div>
}

// frontend/src/pages/Releases.tsx
export default function Releases() {
  return <div>Releases - Coming soon</div>
}

// frontend/src/pages/ReleaseDetail.tsx
export default function ReleaseDetail() {
  return <div>Release Detail - Coming soon</div>
}
```

**Step 4: Create Layout component**

```typescript
// frontend/src/components/Layout.tsx
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useState } from 'react'

export default function Layout() {
  const location = useLocation()
  const [searchQuery, setSearchQuery] = useState('')

  const navLinks = [
    { path: '/', label: 'Dashboard' },
    { path: '/features', label: 'Features' },
    { path: '/options', label: 'Options' },
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <span className="text-xl font-semibold text-gray-900">
                Canvas Feature Tracker
              </span>
            </Link>

            {/* Navigation */}
            <nav className="flex items-center gap-6">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`text-sm font-medium transition-colors ${
                    isActive(link.path)
                      ? 'text-blue-600'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            {/* Search */}
            <div className="w-64">
              <input
                type="text"
                placeholder="Search features, options..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}
```

**Step 5: Verify routing works**

```bash
cd frontend
npm run dev
```

Navigate to http://localhost:5173 and check routes work.

**Step 6: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): set up React Router with layout and placeholder pages"
```

---

## Phase 3: Frontend Pages

> **Note:** This phase should use the `frontend-design:frontend-design` skill to create polished, production-grade UI components. Each page task below provides the data requirements and structure - the frontend-design skill will handle the visual implementation.

### Task 3.1: Implement Dashboard Page

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/components/ReleaseCard.tsx`
- Create: `frontend/src/components/UpcomingChanges.tsx`
- Create: `frontend/src/components/ActivityFeed.tsx`
- Create: `frontend/src/components/StatusPill.tsx`
- Create: `frontend/src/components/DateNavigator.tsx`

**Requirements:**
- Three-column card layout (Release Notes, Deploy Notes, Upcoming Changes)
- Date navigation by publish date (Previous/Next arrows, Current badge)
- Each feature in release notes shows beta/prod dates with subtle status pills
- Recent Activity feed below cards (Q&A + Blog posts)
- "View full" and "Browse archive" links on cards

**Data:** Uses `dashboardApi.get(date?)`

**Use:** `frontend-design:frontend-design` skill to implement

---

### Task 3.2: Implement Features Page

**Files:**
- Modify: `frontend/src/pages/Features.tsx`
- Create: `frontend/src/components/FeatureCard.tsx`
- Create: `frontend/src/components/CategoryFilter.tsx`

**Requirements:**
- Grid of feature cards (45 canonical features)
- Each card shows: name, option count, status summary
- Search bar to filter by name
- Category dropdown filter (Core, Grading, Collaboration, etc.)
- Click card → navigate to feature detail

**Data:** Uses `featuresApi.list(category?)`

**Use:** `frontend-design:frontend-design` skill to implement

---

### Task 3.3: Implement Feature Detail Page

**Files:**
- Modify: `frontend/src/pages/FeatureDetail.tsx`
- Create: `frontend/src/components/OptionsList.tsx`
- Create: `frontend/src/components/AnnouncementsList.tsx`
- Create: `frontend/src/components/CommunityPostsList.tsx`

**Requirements:**
- Header with feature name, category, LLM description
- List of associated feature options with status pills
- Recent announcements section
- Related community posts section
- Back link to Features page

**Data:** Uses `featuresApi.get(featureId)`

**Use:** `frontend-design:frontend-design` skill to implement

---

### Task 3.4: Implement Options Page

**Files:**
- Modify: `frontend/src/pages/Options.tsx`
- Create: `frontend/src/components/OptionRow.tsx`
- Create: `frontend/src/components/StatusFilter.tsx`
- Create: `frontend/src/components/SortSelect.tsx`

**Requirements:**
- List/card view of all feature options
- Each row shows: name, parent feature, status pill, beta/prod dates, description snippet
- Filter by status (All, Pending, Preview, Optional, Default On, Released)
- Filter by feature (dropdown)
- Sort options (Recently updated, Alphabetical, Beta date, Prod date)
- Click row → navigate to option detail

**Data:** Uses `optionsApi.list(params)`

**Use:** `frontend-design:frontend-design` skill to implement

---

### Task 3.5: Implement Option Detail Page

**Files:**
- Modify: `frontend/src/pages/OptionDetail.tsx`
- Create: `frontend/src/components/DeploymentTimeline.tsx`
- Create: `frontend/src/components/ConfigurationTable.tsx`

**Requirements:**
- Header with option name, parent feature link, status pill, meta_summary
- Deployment Status section with visual timeline (Announced → Beta → Prod → Released)
- Configuration section (account/course settings, permissions, affected areas)
- Community Activity section with linked posts
- Announcement History section (chronological list)
- Back link to Options page

**Data:** Uses `optionsApi.get(optionId)`

**Use:** `frontend-design:frontend-design` skill to implement

---

### Task 3.6: Implement Releases Archive Page

**Files:**
- Modify: `frontend/src/pages/Releases.tsx`
- Create: `frontend/src/components/ReleaseRow.tsx`

**Requirements:**
- List of release/deploy notes grouped by month
- Each row shows: title, type badge, announcement count
- Filter by type (All, Release Notes, Deploy Notes)
- Filter by year
- Search bar
- Click row → navigate to release detail

**Data:** Uses `releasesApi.list(params)`

**Use:** `frontend-design:frontend-design` skill to implement

---

### Task 3.7: Implement Release Detail Page

**Files:**
- Modify: `frontend/src/pages/ReleaseDetail.tsx`

**Requirements:**
- Header with title, publish date, link to original
- Full LLM summary
- Features grouped by section (New Features, Updated Features)
- Each feature shows beta/prod dates and links to option detail
- Upcoming changes section if present
- Back link to Archive

**Data:** Uses `releasesApi.get(contentId)`

**Use:** `frontend-design:frontend-design` skill to implement

---

### Task 3.8: Implement Global Search

**Files:**
- Modify: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/SearchModal.tsx`
- Create: `frontend/src/components/SearchResults.tsx`

**Requirements:**
- Search input in header triggers modal/dropdown
- Real-time search as user types (debounced)
- Results grouped: Features, Options, Content
- Each result links to appropriate detail page
- Keyboard navigation (arrow keys, enter to select)

**Data:** Uses `searchApi.search(q)`

**Use:** `frontend-design:frontend-design` skill to implement

---

## Phase 4: Integration & Deployment

### Task 4.1: Configure FastAPI to Serve Frontend

**Files:**
- Modify: `src/api/main.py`

**Step 1: Update main.py to serve static files**

```python
# src/api/main.py (final version)
"""FastAPI application entry point."""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from src.api.routes import dashboard, features, options, releases, search

app = FastAPI(
    title="Canvas Feature Tracker API",
    description="API for tracking Canvas LMS feature options and deployment readiness",
    version="1.0.0",
)

# Register API routers
app.include_router(dashboard.router)
app.include_router(features.router)
app.include_router(options.router)
app.include_router(releases.router)
app.include_router(search.router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# Serve frontend static files
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    # Catch-all route for client-side routing
    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve frontend for all non-API routes."""
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return {"detail": "Not found"}

        # Serve index.html for client-side routing
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"detail": "Frontend not built"}
```

**Step 2: Commit**

```bash
git add src/api/main.py
git commit -m "feat(api): configure FastAPI to serve frontend static files"
```

---

### Task 4.2: Update Docker Configuration

**Files:**
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`

**Step 1: Update Dockerfile to build frontend**

Add to existing Dockerfile (or create new section):

```dockerfile
# Frontend build stage
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Main application stage (modify existing)
# ... existing Python setup ...

# Copy frontend build
COPY --from=frontend-builder /frontend/dist /app/frontend/dist
```

**Step 2: Update docker-compose.yml**

Add environment variable for API:

```yaml
services:
  canvas-rss-aggregator:
    # ... existing config ...
    environment:
      - DATABASE_PATH=/app/data/canvas_digest.db
    ports:
      - "127.0.0.1:8000:8000"
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Step 3: Test Docker build**

```bash
docker-compose build
docker-compose up -d
```

**Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat(docker): add frontend build and API serving configuration"
```

---

### Task 4.3: End-to-End Testing

**Step 1: Build frontend**

```bash
cd frontend
npm run build
cd ..
```

**Step 2: Start API server**

```bash
uvicorn src.api.main:app --reload
```

**Step 3: Test in browser**

- Navigate to http://localhost:8000
- Verify all pages load
- Verify data displays correctly
- Test search functionality
- Test navigation and links

**Step 4: Document any issues**

Create issues for any bugs found during testing.

---

### Task 4.4: Final Commit and Merge Preparation

**Step 1: Run all tests**

```bash
pytest tests/ -v
cd frontend && npm run build && cd ..
```

**Step 2: Update STATE.md**

Document the new website feature.

**Step 3: Final commit**

```bash
git add .
git commit -m "feat: Canvas Feature Tracker website complete

- FastAPI backend with 6 API endpoints
- React frontend with 7 pages
- Dashboard with release/deploy notes and date navigation
- Features and Options browsing with filtering
- Comprehensive option detail view
- Release notes archive
- Global search
- Single container Docker deployment"
```

**Step 4: Ready for merge**

Use `superpowers:finishing-a-development-branch` skill to complete the merge process.

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1.1-1.8 | Backend API (FastAPI endpoints with tests) |
| 2 | 2.1-2.4 | Frontend scaffolding (Vite, React, routing) |
| 3 | 3.1-3.8 | Frontend pages (use frontend-design skill) |
| 4 | 4.1-4.4 | Integration and deployment |

**Total estimated tasks:** 20 tasks across 4 phases

**Key skills to use:**
- `superpowers:executing-plans` - For running through this plan
- `frontend-design:frontend-design` - For Phase 3 UI implementation
- `superpowers:finishing-a-development-branch` - After completion
