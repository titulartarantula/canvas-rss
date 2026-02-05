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
