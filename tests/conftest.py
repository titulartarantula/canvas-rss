"""Pytest configuration and shared fixtures."""

import pytest
import os
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    from utils.database import Database
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    yield db
    db.close()


@pytest.fixture
def sample_content_item():
    """Create a sample content item for testing."""
    from processor.content_processor import ContentItem
    from datetime import datetime

    return ContentItem(
        source="test",
        source_id="test-123",
        title="Test Item",
        url="https://example.com/test",
        content="This is test content about Canvas LMS.",
        published_date=datetime.now()
    )


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response."""
    return {
        "summary": "This is a test summary.",
        "sentiment": "neutral",
        "topics": ["Gradebook", "Assignments"]
    }


# Integration test marker
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires API keys)"
    )
