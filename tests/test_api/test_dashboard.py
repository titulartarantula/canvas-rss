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
