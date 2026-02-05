"""Tests for CLI module."""

import pytest
from unittest.mock import MagicMock, patch


class TestCLIStructure:
    """Tests for CLI module structure."""

    def test_cli_module_exists(self):
        """Test that cli module can be imported."""
        from src import cli
        assert cli is not None

    def test_cli_has_main_function(self):
        """Test that cli has main() function."""
        from src.cli import main
        assert callable(main)

    def test_cli_has_regenerate_command(self):
        """Test that regenerate command is registered."""
        from src.cli import create_parser
        parser = create_parser()
        # Should not raise
        args = parser.parse_args(['regenerate', 'feature', 'speedgrader'])
        assert args.command == 'regenerate'

    def test_cli_has_general_command(self):
        """Test that general command is registered."""
        from src.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(['general', 'list'])
        assert args.command == 'general'


class TestRegenerateFeature:
    """Tests for regenerate feature command."""

    @patch('src.cli.Database')
    @patch('src.cli.ContentProcessor')
    def test_regenerate_feature_calls_processor(self, mock_proc_cls, mock_db_cls):
        """Test that regenerate feature calls the processor."""
        from src.cli import handle_regenerate_feature

        mock_db = MagicMock()
        mock_db.get_feature.return_value = {'feature_id': 'speedgrader', 'name': 'SpeedGrader'}
        mock_db.get_content_for_feature.return_value = [{'content': 'test content'}]
        mock_db_cls.return_value = mock_db

        mock_proc = MagicMock()
        mock_proc.summarize_feature_description.return_value = 'Generated description'
        mock_proc_cls.return_value = mock_proc

        result = handle_regenerate_feature('speedgrader')

        assert result == 0
        mock_proc.summarize_feature_description.assert_called_once()
        mock_db.update_feature_description.assert_called_once()

    @patch('src.cli.Database')
    def test_regenerate_feature_not_found(self, mock_db_cls):
        """Test regenerate feature with unknown ID."""
        from src.cli import handle_regenerate_feature

        mock_db = MagicMock()
        mock_db.get_feature.return_value = None
        mock_db_cls.return_value = mock_db

        result = handle_regenerate_feature('unknown_feature')

        assert result == 1


class TestRegenerateCommands:
    """Tests for all regenerate commands."""

    @patch('src.cli.Database')
    @patch('src.cli.ContentProcessor')
    def test_regenerate_option(self, mock_proc_cls, mock_db_cls):
        """Test regenerate option command."""
        from src.cli import handle_regenerate_option

        mock_db = MagicMock()
        mock_db.get_feature_option.return_value = {
            'option_id': 'test_opt',
            'name': 'Test Option',
            'feature_id': 'speedgrader'
        }
        mock_db.get_feature.return_value = {'name': 'SpeedGrader'}
        mock_db.get_latest_content_for_option.return_value = []
        mock_db_cls.return_value = mock_db

        mock_proc = MagicMock()
        mock_proc.summarize_feature_option_description.return_value = 'Description'
        mock_proc_cls.return_value = mock_proc

        result = handle_regenerate_option('test_opt')
        assert result == 0
        mock_db.update_feature_option_description.assert_called_once()

    @patch('src.cli.Database')
    @patch('src.cli.ContentProcessor')
    def test_regenerate_meta_summary(self, mock_proc_cls, mock_db_cls):
        """Test regenerate meta-summary command."""
        from src.cli import handle_regenerate_meta_summary

        mock_db = MagicMock()
        mock_db.get_feature_option.return_value = {
            'option_id': 'test_opt',
            'name': 'Test Option',
            'feature_id': 'speedgrader',
            'implementation_status': 'In preview'
        }
        mock_db.get_feature.return_value = {'name': 'SpeedGrader'}
        mock_db.get_latest_content_for_option.return_value = []
        mock_db_cls.return_value = mock_db

        mock_proc = MagicMock()
        mock_proc.generate_meta_summary.return_value = 'Meta summary'
        mock_proc_cls.return_value = mock_proc

        result = handle_regenerate_meta_summary('test_opt')
        assert result == 0
        mock_db.update_feature_option_meta_summary.assert_called_once()

    @patch('src.cli.Database')
    def test_regenerate_features_missing(self, mock_db_cls):
        """Test regenerate features --missing --dry-run."""
        from src.cli import handle_regenerate_features

        mock_db = MagicMock()
        mock_db.get_features_missing_description.return_value = [
            {'feature_id': 'a', 'name': 'A'},
            {'feature_id': 'b', 'name': 'B'},
        ]
        mock_db_cls.return_value = mock_db

        result = handle_regenerate_features(missing_only=True, dry_run=True)
        assert result == 0


class TestGeneralTriage:
    """Tests for general triage command."""

    def test_suggest_matches_returns_ranked_list(self):
        """Test that suggest_matches returns ranked suggestions."""
        from src.cli import suggest_matches

        suggestions = suggest_matches(
            title="Tips for using SpeedGrader with large classes",
            content="Many instructors struggle with grading..."
        )

        assert len(suggestions) > 0
        assert suggestions[0]['feature_id'] == 'speedgrader'
        assert 'confidence' in suggestions[0]

    def test_suggest_matches_handles_no_match(self):
        """Test suggest_matches with unrelated content."""
        from src.cli import suggest_matches

        suggestions = suggest_matches(
            title="Random unrelated topic",
            content="This has nothing to do with Canvas features"
        )

        # Should still return something, even if low confidence
        assert isinstance(suggestions, list)

    @patch('src.cli.Database')
    def test_general_list(self, mock_db_cls):
        """Test general list command."""
        from src.cli import handle_general_list

        mock_db = MagicMock()
        mock_db.get_content_by_feature.return_value = [
            {'source_id': 'blog_123', 'title': 'Test', 'first_posted': '2026-02-01'}
        ]
        mock_db_cls.return_value = mock_db

        result = handle_general_list()
        assert result == 0

    @patch('src.cli.Database')
    def test_general_list_empty(self, mock_db_cls):
        """Test general list with no items."""
        from src.cli import handle_general_list

        mock_db = MagicMock()
        mock_db.get_content_by_feature.return_value = []
        mock_db_cls.return_value = mock_db

        result = handle_general_list()
        assert result == 0

    @patch('src.cli.Database')
    def test_general_list_with_days_filter(self, mock_db_cls):
        """Test general list with --days filter."""
        from src.cli import handle_general_list

        mock_db = MagicMock()
        mock_db.get_content_by_feature.return_value = [
            {'source_id': 'blog_123', 'title': 'Test', 'first_posted': '2026-02-01'}
        ]
        mock_db_cls.return_value = mock_db

        result = handle_general_list(days=7)
        assert result == 0

    def test_suggest_matches_boosts_title_match(self):
        """Test that matches in title get boosted confidence."""
        from src.cli import suggest_matches

        # Use 'Rich Content Editor' - multi-word feature that won't hit cap
        # Title match: RCE keywords in title
        title_match = suggest_matches(
            title="Rich Content Editor issues",
            content="Having some problems."
        )

        # Content match: RCE keywords in content only
        content_only = suggest_matches(
            title="Having some problems",
            content="Issues with Rich Content Editor."
        )

        # Both should find rich_content_editor
        assert any(s['feature_id'] == 'rich_content_editor' for s in title_match)
        assert any(s['feature_id'] == 'rich_content_editor' for s in content_only)

        # Title match should have higher confidence due to title boost
        title_conf = next(s['confidence'] for s in title_match if s['feature_id'] == 'rich_content_editor')
        content_conf = next(s['confidence'] for s in content_only if s['feature_id'] == 'rich_content_editor')
        assert title_conf > content_conf
