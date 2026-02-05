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

    options = data["options"]
    assert len(options) >= 1

    # Verify options with beta_date come first, nulls at end
    beta_dates = [o.get("beta_date") for o in options]
    non_null_indices = [i for i, d in enumerate(beta_dates) if d is not None]
    null_indices = [i for i, d in enumerate(beta_dates) if d is None]

    # All non-null indices should come before null indices
    if non_null_indices and null_indices:
        assert max(non_null_indices) < min(null_indices), "Options with beta_date should come before those without"

    # Non-null dates should be in ascending order
    non_null_dates = [beta_dates[i] for i in non_null_indices]
    assert non_null_dates == sorted(non_null_dates), "Beta dates should be sorted ascending"


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
