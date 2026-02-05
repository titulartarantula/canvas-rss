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
