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
