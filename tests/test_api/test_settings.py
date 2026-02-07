"""Tests for settings API endpoints."""
import sqlite3
import pytest
from fastapi.testclient import TestClient


class TestSettingsAPI:
    """Tests for /api/settings endpoints."""

    def test_get_settings_empty(self, client):
        """GET /api/settings returns empty list when no settings exist."""
        response = client.get("/api/settings")
        assert response.status_code == 200
        assert response.json() == {"settings": []}

    def test_get_settings_returns_data(self, client, populated_db):
        """GET /api/settings returns feature settings."""
        conn = sqlite3.connect(populated_db)
        conn.execute("""
            INSERT INTO feature_settings (setting_id, feature_id, name, status, last_updated)
            VALUES ('speed-fix', 'assignments', 'Speed Fix for Large Courses', 'active', '2026-02-07')
        """)
        conn.commit()
        conn.close()

        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert len(data["settings"]) == 1
        assert data["settings"][0]["setting_id"] == "speed-fix"

    def test_get_settings_filter_by_feature(self, client, populated_db):
        """GET /api/settings?feature=assignments filters correctly."""
        conn = sqlite3.connect(populated_db)
        conn.execute("""
            INSERT INTO feature_settings (setting_id, feature_id, name, status)
            VALUES ('s1', 'assignments', 'Setting 1', 'active')
        """)
        conn.execute("""
            INSERT INTO feature_settings (setting_id, feature_id, name, status)
            VALUES ('s2', 'gradebook', 'Setting 2', 'active')
        """)
        conn.commit()
        conn.close()

        response = client.get("/api/settings?feature=assignments")
        assert response.status_code == 200
        data = response.json()
        assert len(data["settings"]) == 1
        assert data["settings"][0]["feature_id"] == "assignments"

    def test_get_setting_detail(self, client, populated_db):
        """GET /api/settings/{setting_id} returns detail."""
        conn = sqlite3.connect(populated_db)
        conn.execute("""
            INSERT INTO feature_settings (setting_id, feature_id, name, status)
            VALUES ('speed-fix', 'assignments', 'Speed Fix', 'active')
        """)
        conn.commit()
        conn.close()

        response = client.get("/api/settings/speed-fix")
        assert response.status_code == 200
        data = response.json()
        assert data["setting_id"] == "speed-fix"
        assert data["feature"]["feature_id"] == "assignments"

    def test_get_setting_detail_not_found(self, client):
        """GET /api/settings/{setting_id} returns 404 for missing setting."""
        response = client.get("/api/settings/nonexistent")
        assert response.status_code == 404


class TestFeatureDetailIncludesSettings:
    """Test that feature detail includes settings."""

    def test_feature_detail_includes_settings(self, client, populated_db):
        """GET /api/features/{id} includes settings array."""
        conn = sqlite3.connect(populated_db)
        conn.execute("""
            INSERT INTO feature_settings (setting_id, feature_id, name, status)
            VALUES ('speed-fix', 'assignments', 'Speed Fix', 'active')
        """)
        conn.commit()
        conn.close()

        response = client.get("/api/features/assignments")
        assert response.status_code == 200
        data = response.json()
        assert "settings" in data
        assert len(data["settings"]) == 1
        assert data["settings"][0]["setting_id"] == "speed-fix"

    def test_feature_detail_includes_both_options_and_settings(self, client, populated_db):
        """GET /api/features/{id} returns both options and settings."""
        conn = sqlite3.connect(populated_db)
        conn.execute("""
            INSERT INTO feature_settings (setting_id, feature_id, name, status)
            VALUES ('speed-fix', 'assignments', 'Speed Fix', 'active')
        """)
        conn.commit()
        conn.close()

        response = client.get("/api/features/assignments")
        assert response.status_code == 200
        data = response.json()
        assert "options" in data
        assert "settings" in data
        # assignments has 'document_processor' option from populated_db
        assert len(data["options"]) >= 1
        assert len(data["settings"]) == 1
