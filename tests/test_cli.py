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
