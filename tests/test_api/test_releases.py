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


def test_get_releases_filtered_by_search(client, populated_db):
    """Test filtering releases by search term in title."""
    response = client.get("/api/releases?search=Release")
    assert response.status_code == 200
    data = response.json()

    # Should find release_note_2026-02-21 which has "Release" in title
    assert len(data["releases"]) >= 1
    for release in data["releases"]:
        assert "Release" in release["title"]


def test_get_release_detail_not_found(client, populated_db):
    """Test 404 for non-existent release."""
    response = client.get("/api/releases/nonexistent")
    assert response.status_code == 404
