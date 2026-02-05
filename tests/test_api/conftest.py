"""Pytest fixtures for API tests."""
import pytest
import sqlite3
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
