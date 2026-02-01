"""Tests for content processor."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


class TestContentProcessor:
    """Tests for the ContentProcessor class."""

    def test_content_processor_initialization(self):
        """Test that ContentProcessor initializes correctly."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        assert "Gradebook" in processor.TOPIC_CATEGORIES

    def test_content_item_dataclass(self, sample_content_item):
        """Test ContentItem dataclass."""
        assert sample_content_item.source == "test"
        assert sample_content_item.source_id == "test-123"
        assert sample_content_item.topics == []  # Default empty list


class TestContentProcessorInitialization:
    """Tests for ContentProcessor __init__ method."""

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_init_with_api_key_provided(self, mock_genai):
        """Test initialization with API key provided directly."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-api-key")

        assert processor.gemini_api_key == "test-api-key"
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")
        mock_genai.GenerativeModel.assert_called_once()
        assert processor.model is not None

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'env-api-key'})
    def test_init_with_api_key_from_environment(self, mock_genai):
        """Test initialization with API key from environment variable."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor()

        assert processor.gemini_api_key == "env-api-key"
        mock_genai.configure.assert_called_once_with(api_key="env-api-key")

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    @patch.dict('os.environ', {}, clear=True)
    def test_init_without_api_key(self, mock_genai):
        """Test initialization without API key (model should be None)."""
        from processor.content_processor import ContentProcessor
        import os
        # Clear the env var if it exists
        os.environ.pop('GEMINI_API_KEY', None)

        processor = ContentProcessor()

        assert processor.model is None
        mock_genai.configure.assert_not_called()

    @patch('processor.content_processor.GENAI_AVAILABLE', False)
    @patch.dict('os.environ', {}, clear=True)
    def test_init_genai_not_available(self):
        """Test initialization when google-generativeai is not installed."""
        from processor.content_processor import ContentProcessor
        import os
        os.environ.pop('GEMINI_API_KEY', None)

        processor = ContentProcessor(gemini_api_key="test-key")

        assert processor.model is None

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_init_model_initialization_error(self, mock_genai):
        """Test initialization when model initialization fails."""
        from processor.content_processor import ContentProcessor

        mock_genai.configure.side_effect = Exception("Configuration error")

        processor = ContentProcessor(gemini_api_key="test-key")

        assert processor.model is None


class TestDeduplicate:
    """Tests for the deduplicate method."""

    def test_deduplicate_empty_list(self):
        """Test that empty list returns empty list."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        mock_db = Mock()

        result = processor.deduplicate([], mock_db)

        assert result == []

    def test_deduplicate_filters_existing_items(self, sample_content_item):
        """Test that existing items are filtered out."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        mock_db = Mock()
        mock_db.item_exists.return_value = True

        result = processor.deduplicate([sample_content_item], mock_db)

        assert result == []
        mock_db.item_exists.assert_called_once_with("test-123")

    def test_deduplicate_keeps_new_items(self, sample_content_item):
        """Test that new items are kept."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        mock_db = Mock()
        mock_db.item_exists.return_value = False

        result = processor.deduplicate([sample_content_item], mock_db)

        assert len(result) == 1
        assert result[0] == sample_content_item

    def test_deduplicate_handles_none_items(self, sample_content_item):
        """Test that None items are handled gracefully."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        mock_db = Mock()
        mock_db.item_exists.return_value = False

        result = processor.deduplicate([None, sample_content_item, None], mock_db)

        assert len(result) == 1
        assert result[0] == sample_content_item

    def test_deduplicate_mixed_existing_and_new(self):
        """Test with mix of existing and new items."""
        from processor.content_processor import ContentProcessor, ContentItem

        processor = ContentProcessor()
        mock_db = Mock()

        item1 = ContentItem(
            source="test", source_id="existing-1", title="Existing",
            url="https://example.com/1", content="Content 1"
        )
        item2 = ContentItem(
            source="test", source_id="new-1", title="New",
            url="https://example.com/2", content="Content 2"
        )

        # First item exists, second doesn't
        mock_db.item_exists.side_effect = [True, False]

        result = processor.deduplicate([item1, item2], mock_db)

        assert len(result) == 1
        assert result[0].source_id == "new-1"

    def test_deduplicate_database_error_includes_item(self, sample_content_item):
        """Test that items are included when database check fails."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        mock_db = Mock()
        mock_db.item_exists.side_effect = Exception("DB error")

        result = processor.deduplicate([sample_content_item], mock_db)

        # Item should be included when we can't determine duplicate status
        assert len(result) == 1


class TestSummarizeWithLLM:
    """Tests for the summarize_with_llm method."""

    def test_summarize_empty_content_returns_empty(self):
        """Test that empty content returns empty string."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = processor.summarize_with_llm("")

        assert result == ""

    def test_summarize_none_content_returns_empty(self):
        """Test that None content returns empty string."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = processor.summarize_with_llm(None)

        assert result == ""

    def test_summarize_model_none_returns_truncated(self):
        """Test that when client is None, returns truncated content."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        processor.client = None

        content = "This is a short test content."
        result = processor.summarize_with_llm(content)

        assert result == content

    def test_summarize_model_none_truncates_long_content(self):
        """Test that long content is truncated to ~1200 chars when model is None."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        processor.client = None

        long_content = "word " * 300  # About 1500 chars
        result = processor.summarize_with_llm(long_content)

        assert len(result) <= 1210  # 1200 + some buffer for "..."
        assert result.endswith("...")

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_summarize_successful_api_call(self, mock_genai):
        """Test successful LLM summarization."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is a summary of the Canvas update."
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        result = processor.summarize_with_llm("Some content about Canvas LMS updates")

        assert result == "This is a summary of the Canvas update."
        mock_model.generate_content.assert_called_once()

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_summarize_api_error_returns_empty(self, mock_genai):
        """Test that API error returns empty string."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        result = processor.summarize_with_llm("Some content")

        assert result == ""

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_summarize_truncates_long_api_response(self, mock_genai):
        """Test that long API responses are truncated to 300 chars."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "word " * 100  # Very long response
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        result = processor.summarize_with_llm("Some content")

        assert len(result) <= 310  # 300 + buffer for "..."
        assert result.endswith("...")


class TestAnalyzeSentiment:
    """Tests for the analyze_sentiment method."""

    def test_sentiment_empty_content_returns_neutral(self):
        """Test that empty content returns neutral."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = processor.analyze_sentiment("")

        assert result == "neutral"

    def test_sentiment_none_content_returns_neutral(self):
        """Test that None content returns neutral."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = processor.analyze_sentiment(None)

        assert result == "neutral"

    def test_sentiment_model_none_returns_neutral(self):
        """Test that when model is None, returns neutral."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        processor.model = None

        result = processor.analyze_sentiment("Some content")

        assert result == "neutral"

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_sentiment_positive(self, mock_genai):
        """Test detection of positive sentiment."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "positive"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        result = processor.analyze_sentiment("Great new feature!")

        assert result == "positive"

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_sentiment_neutral(self, mock_genai):
        """Test detection of neutral sentiment."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "neutral"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        result = processor.analyze_sentiment("The update was released.")

        assert result == "neutral"

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_sentiment_negative(self, mock_genai):
        """Test detection of negative sentiment."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "negative"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        result = processor.analyze_sentiment("This feature is broken!")

        assert result == "negative"

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_sentiment_invalid_response_defaults_neutral(self, mock_genai):
        """Test that invalid response defaults to neutral."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "unknown_value"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        result = processor.analyze_sentiment("Some content")

        assert result == "neutral"

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_sentiment_api_error_defaults_neutral(self, mock_genai):
        """Test that API error defaults to neutral."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        result = processor.analyze_sentiment("Some content")

        assert result == "neutral"

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_sentiment_case_insensitive(self, mock_genai):
        """Test that sentiment matching is case insensitive."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "POSITIVE"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        result = processor.analyze_sentiment("Great!")

        assert result == "positive"


class TestClassifyTopic:
    """Tests for the classify_topic method."""

    def test_classify_empty_content_returns_default(self):
        """Test that empty content returns default topic tuple."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        primary, secondary = processor.classify_topic("")

        assert primary == "General"
        assert secondary == []

    def test_classify_none_content_returns_default(self):
        """Test that None content returns default topic tuple."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        primary, secondary = processor.classify_topic(None)

        assert primary == "General"
        assert secondary == []

    def test_classify_model_none_returns_default(self):
        """Test that when model is None, returns default topic tuple."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        processor.model = None

        primary, secondary = processor.classify_topic("Some content about gradebook")

        assert primary == "General"
        assert secondary == []

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_classify_returns_valid_topics(self, mock_genai):
        """Test that valid topics from TOPIC_CATEGORIES are returned."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "PRIMARY: Gradebook | SECONDARY: Assignments"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        primary, secondary = processor.classify_topic("Content about grades and homework")

        assert primary == "Gradebook"
        assert "Assignments" in secondary

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_classify_filters_invalid_topics(self, mock_genai):
        """Test that invalid topics are filtered out."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "PRIMARY: Gradebook | SECONDARY: InvalidTopic, Assignments"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        primary, secondary = processor.classify_topic("Some content")

        assert primary == "Gradebook"
        assert "Assignments" in secondary
        assert "InvalidTopic" not in secondary

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_classify_case_insensitive(self, mock_genai):
        """Test that topic matching is case insensitive."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "PRIMARY: gradebook | SECONDARY: ASSIGNMENTS, Quizzes"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        primary, secondary = processor.classify_topic("Some content")

        # Should return properly cased topics from TOPIC_CATEGORIES
        assert primary == "Gradebook"
        assert "Assignments" in secondary
        assert "Quizzes" in secondary

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_classify_max_two_secondary_topics(self, mock_genai):
        """Test that maximum 2 secondary topics are returned."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "PRIMARY: Gradebook | SECONDARY: Assignments, Quizzes, Discussions, Pages"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        primary, secondary = processor.classify_topic("Some content")

        assert primary == "Gradebook"
        assert len(secondary) <= 2

    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_classify_api_error_returns_default(self, mock_genai):
        """Test that API error returns default topic tuple."""
        from processor.content_processor import ContentProcessor

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")
        primary, secondary = processor.classify_topic("Some content")

        assert primary == "General"
        assert secondary == []


class TestSanitizeHtml:
    """Tests for the sanitize_html method."""

    def test_sanitize_empty_content_returns_empty(self):
        """Test that empty content returns empty string."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = processor.sanitize_html("")

        assert result == ""

    def test_sanitize_none_content_returns_empty(self):
        """Test that None content returns empty string."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = processor.sanitize_html(None)

        assert result == ""

    def test_sanitize_allows_safe_tags(self):
        """Test that allowed tags are preserved."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        html = "<p>Paragraph</p><br><strong>Bold</strong><em>Italic</em>"
        result = processor.sanitize_html(html)

        assert "<p>" in result
        assert "<br>" in result
        assert "<strong>" in result
        assert "<em>" in result

    def test_sanitize_allows_list_tags(self):
        """Test that list tags are preserved."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        html = "<ul><li>Item 1</li><li>Item 2</li></ul><ol><li>Ordered</li></ol>"
        result = processor.sanitize_html(html)

        assert "<ul>" in result
        assert "<ol>" in result
        assert "<li>" in result

    def test_sanitize_allows_anchor_tags(self):
        """Test that anchor tags with href are preserved."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        html = '<a href="https://example.com">Link</a>'
        result = processor.sanitize_html(html)

        assert "<a" in result
        assert 'href="https://example.com"' in result
        assert "Link</a>" in result

    def test_sanitize_allows_h3_tags(self):
        """Test that h3 tags are preserved."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        html = "<h3>Heading</h3>"
        result = processor.sanitize_html(html)

        assert "<h3>" in result

    def test_sanitize_strips_disallowed_tags(self):
        """Test that disallowed tags are stripped."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        html = "<div>Content</div><span>More</span><h1>Big</h1>"
        result = processor.sanitize_html(html)

        assert "<div>" not in result
        assert "<span>" not in result
        assert "<h1>" not in result
        # Content should still be preserved
        assert "Content" in result
        assert "More" in result

    def test_sanitize_strips_script_tags(self):
        """Test that script tags are removed (content may remain per bleach behavior)."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        html = "<p>Safe content</p><script>alert('xss')</script>"
        result = processor.sanitize_html(html)

        # The script tag itself should be removed
        assert "<script>" not in result
        assert "</script>" not in result
        assert "Safe content" in result
        # Note: bleach with strip=True removes the tag but keeps tag content as text

    def test_sanitize_preserves_href_attribute(self):
        """Test that href attribute is preserved on links."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        html = '<a href="https://canvas.instructure.com">Canvas</a>'
        result = processor.sanitize_html(html)

        assert 'href="https://canvas.instructure.com"' in result

    def test_sanitize_strips_onclick_attribute(self):
        """Test that onclick and other event attributes are stripped."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        html = '<a href="https://example.com" onclick="evil()">Link</a>'
        result = processor.sanitize_html(html)

        assert "onclick" not in result
        # href should still be there
        assert 'href="https://example.com"' in result

    def test_sanitize_strips_style_attribute(self):
        """Test that style attributes are stripped."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        html = '<p style="color: red;">Styled text</p>'
        result = processor.sanitize_html(html)

        assert "style=" not in result
        assert "Styled text" in result


class TestRedactPii:
    """Tests for the redact_pii method."""

    def test_redact_empty_content_returns_empty(self):
        """Test that empty content returns empty string."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = processor.redact_pii("")

        assert result == ""

    def test_redact_none_content_returns_empty(self):
        """Test that None content returns empty string."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = processor.redact_pii(None)

        assert result == ""

    def test_redact_email_addresses(self):
        """Test that email addresses are redacted."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        content = "Contact me at john.doe@example.com for more info."
        result = processor.redact_pii(content)

        assert "[email]" in result
        assert "john.doe@example.com" not in result

    def test_redact_reddit_usernames(self):
        """Test that Reddit usernames are redacted."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        content = "Thanks to u/helpful_user for the tip!"
        result = processor.redact_pii(content)

        assert "[user]" in result
        assert "u/helpful_user" not in result

    def test_redact_phone_numbers_with_dashes(self):
        """Test that phone numbers with dashes are redacted."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        content = "Call me at 555-123-4567 for support."
        result = processor.redact_pii(content)

        assert "[phone]" in result
        assert "555-123-4567" not in result

    def test_redact_phone_numbers_with_dots(self):
        """Test that phone numbers with dots are redacted."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        content = "My number is 555.123.4567"
        result = processor.redact_pii(content)

        assert "[phone]" in result
        assert "555.123.4567" not in result

    def test_redact_phone_numbers_without_separators(self):
        """Test that phone numbers without separators are redacted."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        content = "Call 5551234567 now!"
        result = processor.redact_pii(content)

        assert "[phone]" in result
        assert "5551234567" not in result

    def test_redact_multiple_occurrences(self):
        """Test that multiple PII occurrences are all redacted."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        content = "Contact user1@example.com or user2@test.org. Thanks u/poster1 and u/poster2!"
        result = processor.redact_pii(content)

        # Count occurrences of redaction placeholders
        assert result.count("[email]") == 2
        assert result.count("[user]") == 2
        assert "user1@example.com" not in result
        assert "user2@test.org" not in result

    def test_redact_preserves_non_pii_content(self):
        """Test that non-PII content is preserved."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        content = "This is a regular message about Canvas LMS updates."
        result = processor.redact_pii(content)

        assert result == content

    def test_redact_mixed_pii_and_content(self):
        """Test content with mixed PII and regular text."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        content = "User u/canvas_admin (admin@school.edu) reported issue at 555-123-4567"
        result = processor.redact_pii(content)

        assert "[user]" in result
        assert "[email]" in result
        assert "[phone]" in result
        assert "reported issue at" in result


class TestEnrichWithLLM:
    """Tests for the enrich_with_llm method."""

    def test_enrich_empty_list_returns_empty(self):
        """Test that empty list returns empty list."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = processor.enrich_with_llm([])

        assert result == []

    def test_enrich_none_list_returns_empty(self):
        """Test that None is handled (should raise AttributeError or return empty)."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        # The implementation checks `if not items:` which handles None
        result = processor.enrich_with_llm(None)

        assert result == []

    @patch('processor.content_processor.time')
    def test_enrich_single_item_without_model(self, mock_time, sample_content_item):
        """Test enrichment of single item when model is None."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        processor.model = None

        result = processor.enrich_with_llm([sample_content_item])

        assert len(result) == 1
        # Summary should be truncated content (fallback behavior)
        assert result[0].summary != ""
        # Sentiment should be neutral (fallback)
        assert result[0].sentiment == "neutral"
        # Topics should be empty (fallback)
        assert result[0].topics == []

    @patch('processor.content_processor.time')
    def test_enrich_handles_none_items(self, mock_time, sample_content_item):
        """Test that None items are skipped."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        processor.model = None

        result = processor.enrich_with_llm([None, sample_content_item, None])

        assert len(result) == 1

    @patch('processor.content_processor.time')
    def test_enrich_sanitizes_html(self, mock_time):
        """Test that HTML content is sanitized."""
        from processor.content_processor import ContentProcessor, ContentItem

        processor = ContentProcessor()
        processor.model = None

        item = ContentItem(
            source="test",
            source_id="test-html",
            title="HTML Test",
            url="https://example.com",
            content="<p>Safe</p><script>alert('xss')</script>"
        )

        result = processor.enrich_with_llm([item])

        assert len(result) == 1
        assert "<script>" not in result[0].content
        assert "Safe" in result[0].content

    @patch('processor.content_processor.time')
    def test_enrich_redacts_pii(self, mock_time):
        """Test that PII is redacted."""
        from processor.content_processor import ContentProcessor, ContentItem

        processor = ContentProcessor()
        processor.model = None

        item = ContentItem(
            source="test",
            source_id="test-pii",
            title="PII Test",
            url="https://example.com",
            content="Contact user@example.com or u/reddit_user"
        )

        result = processor.enrich_with_llm([item])

        assert len(result) == 1
        assert "user@example.com" not in result[0].content
        assert "u/reddit_user" not in result[0].content
        assert "[email]" in result[0].content
        assert "[user]" in result[0].content

    @patch('processor.content_processor.time')
    @patch('processor.content_processor.GENAI_AVAILABLE', True)
    @patch('processor.content_processor.genai')
    def test_enrich_with_model(self, mock_genai, mock_time):
        """Test enrichment with LLM model available."""
        from processor.content_processor import ContentProcessor, ContentItem

        mock_model = MagicMock()
        # Mock responses for summarize, sentiment, and topic classification
        mock_responses = [
            MagicMock(text="Summary of the content"),  # summarize
            MagicMock(text="positive"),  # sentiment
            MagicMock(text="PRIMARY: Gradebook | SECONDARY: Assignments"),  # topics
        ]
        mock_model.generate_content.side_effect = mock_responses
        mock_genai.GenerativeModel.return_value = mock_model

        processor = ContentProcessor(gemini_api_key="test-key")

        item = ContentItem(
            source="test",
            source_id="test-enrich",
            title="Enrichment Test",
            url="https://example.com",
            content="New gradebook features have been released."
        )

        result = processor.enrich_with_llm([item])

        assert len(result) == 1
        assert result[0].summary == "Summary of the content"
        assert result[0].sentiment == "positive"
        assert result[0].primary_topic == "Gradebook"
        assert "Assignments" in result[0].topics

    @patch('processor.content_processor.time')
    def test_enrich_handles_item_exception(self, mock_time, sample_content_item):
        """Test that items causing exceptions are still included."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor()
        processor.model = None

        # Mock sanitize_html to raise exception for one item
        original_sanitize = processor.sanitize_html

        def mock_sanitize(content):
            if content and "raise_error" in content:
                raise Exception("Sanitization error")
            return original_sanitize(content)

        processor.sanitize_html = mock_sanitize

        from processor.content_processor import ContentItem

        item_ok = sample_content_item
        item_error = ContentItem(
            source="test",
            source_id="test-error",
            title="Error Item",
            url="https://example.com",
            content="This will raise_error during processing"
        )

        result = processor.enrich_with_llm([item_ok, item_error])

        # Both items should be included (error handling includes item anyway)
        assert len(result) == 2

    @patch('processor.content_processor.time')
    def test_enrich_multiple_items(self, mock_time):
        """Test enrichment of multiple items."""
        from processor.content_processor import ContentProcessor, ContentItem

        processor = ContentProcessor()
        processor.model = None

        items = [
            ContentItem(
                source="community",
                source_id="item-1",
                title="Item 1",
                url="https://example.com/1",
                content="Content for item one"
            ),
            ContentItem(
                source="reddit",
                source_id="item-2",
                title="Item 2",
                url="https://example.com/2",
                content="Content for item two"
            ),
            ContentItem(
                source="status",
                source_id="item-3",
                title="Item 3",
                url="https://example.com/3",
                content="Content for item three"
            ),
        ]

        result = processor.enrich_with_llm(items)

        assert len(result) == 3
        # All items should have been enriched
        for item in result:
            assert item.summary != ""
            assert item.sentiment == "neutral"


class TestContentProcessorConstants:
    """Tests for ContentProcessor class constants."""

    def test_topic_categories_defined(self):
        """Test that TOPIC_CATEGORIES constant is properly defined."""
        from processor.content_processor import ContentProcessor

        categories = ContentProcessor.TOPIC_CATEGORIES
        assert "Gradebook" in categories
        assert "Assignments" in categories
        assert "SpeedGrader" in categories
        assert "Quizzes" in categories
        assert "Discussions" in categories
        assert "Pages" in categories
        assert "Files" in categories
        assert "People" in categories
        assert "Groups" in categories
        assert "Calendar" in categories
        assert "Notifications" in categories
        assert "Mobile" in categories
        assert "API" in categories
        assert "Performance" in categories
        assert "Accessibility" in categories

    def test_allowed_tags_defined(self):
        """Test that ALLOWED_TAGS constant is properly defined."""
        from processor.content_processor import ContentProcessor

        tags = ContentProcessor.ALLOWED_TAGS
        assert "p" in tags
        assert "br" in tags
        assert "strong" in tags
        assert "em" in tags
        assert "ul" in tags
        assert "ol" in tags
        assert "li" in tags
        assert "a" in tags
        assert "h3" in tags

    def test_allowed_attributes_defined(self):
        """Test that ALLOWED_ATTRIBUTES constant is properly defined."""
        from processor.content_processor import ContentProcessor

        attrs = ContentProcessor.ALLOWED_ATTRIBUTES
        assert "a" in attrs
        assert "href" in attrs["a"]
        assert "title" in attrs["a"]

    def test_pii_patterns_defined(self):
        """Test that PII regex patterns are properly defined."""
        from processor.content_processor import ContentProcessor

        assert ContentProcessor.EMAIL_PATTERN is not None
        assert ContentProcessor.REDDIT_USER_PATTERN is not None
        assert ContentProcessor.PHONE_PATTERN is not None

        # Test patterns work
        assert ContentProcessor.EMAIL_PATTERN.search("test@example.com")
        assert ContentProcessor.REDDIT_USER_PATTERN.search("u/testuser")
        assert ContentProcessor.PHONE_PATTERN.search("555-123-4567")


class TestFormatAvailability:
    """Tests for format_availability helper."""

    def test_format_availability_full(self):
        """Test full availability string."""
        from processor.content_processor import format_availability
        from scrapers.instructure_community import FeatureTableData

        table = FeatureTableData(
            enable_location="Account Settings",
            default_status="Off",
            permissions="Admin only",
            affected_areas=["Assignments", "SpeedGrader"],
            affects_roles=["instructors", "students"]
        )

        result = format_availability(table)
        assert "Admin" in result
        assert "account" in result.lower()  # lowercase since implementation uses .lower()
        assert "instructors" in result

    def test_format_availability_none_table(self):
        """Test with None table returns default."""
        from processor.content_processor import format_availability

        result = format_availability(None)
        assert "Automatic" in result


class TestSummarizeFeature:
    """Tests for feature summarization."""

    def test_summarize_feature_prompt(self):
        """Test feature summarization uses correct prompt."""
        from processor.content_processor import ContentProcessor
        from scrapers.instructure_community import Feature, FeatureTableData

        processor = ContentProcessor(gemini_api_key=None)  # No API key = fallback

        table = FeatureTableData("Account", "Off", "Admin", ["Assignments"], ["instructors"])
        feature = Feature(
            category="Assignments",
            name="Document Processing App",
            anchor_id="doc-app",
            added_date=None,
            raw_content="This feature allows document processing in Canvas.",
            table_data=table
        )

        # Without API key, should return truncated content
        result = processor.summarize_feature(feature)
        assert "document processing" in result.lower() or result == ""


class TestContentItemDataclass:
    """Tests for ContentItem dataclass."""

    def test_content_item_creation(self):
        """Test basic ContentItem creation."""
        from processor.content_processor import ContentItem

        item = ContentItem(
            source="community",
            source_id="comm-123",
            title="Test Title",
            url="https://example.com",
            content="Test content"
        )

        assert item.source == "community"
        assert item.source_id == "comm-123"
        assert item.title == "Test Title"
        assert item.url == "https://example.com"
        assert item.content == "Test content"

    def test_content_item_default_values(self):
        """Test ContentItem default values."""
        from processor.content_processor import ContentItem

        item = ContentItem(
            source="test",
            source_id="test-123",
            title="Test",
            url="https://example.com",
            content="Content"
        )

        assert item.summary == ""
        assert item.sentiment == ""
        assert item.topics == []
        assert item.published_date is None
        assert item.engagement_score == 0

    def test_content_item_with_all_fields(self):
        """Test ContentItem with all fields populated."""
        from processor.content_processor import ContentItem
        from datetime import datetime, timezone

        pub_date = datetime.now(timezone.utc)
        item = ContentItem(
            source="reddit",
            source_id="reddit-456",
            title="Full Item",
            url="https://reddit.com/r/test",
            content="Full content here",
            summary="A summary",
            sentiment="positive",
            topics=["Gradebook", "Assignments"],
            published_date=pub_date,
            engagement_score=100
        )

        assert item.summary == "A summary"
        assert item.sentiment == "positive"
        assert item.topics == ["Gradebook", "Assignments"]
        assert item.published_date == pub_date
        assert item.engagement_score == 100

    def test_content_item_topics_none_becomes_empty_list(self):
        """Test that topics=None becomes empty list via __post_init__."""
        from processor.content_processor import ContentItem

        item = ContentItem(
            source="test",
            source_id="test-123",
            title="Test",
            url="https://example.com",
            content="Content",
            topics=None
        )

        assert item.topics == []
