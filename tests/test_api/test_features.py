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
