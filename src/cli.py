"""Command-line interface for canvas-rss management."""

import argparse
import sys
from typing import Optional


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog='canvas-rss',
        description='Canvas RSS Aggregator CLI'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Regenerate command
    regen_parser = subparsers.add_parser('regenerate', help='Regenerate LLM summaries')
    regen_subparsers = regen_parser.add_subparsers(dest='regen_type', help='What to regenerate')

    # regenerate feature <id>
    regen_feature = regen_subparsers.add_parser('feature', help='Regenerate feature description')
    regen_feature.add_argument('feature_id', help='Feature ID to regenerate')

    # regenerate option <id>
    regen_option = regen_subparsers.add_parser('option', help='Regenerate option description')
    regen_option.add_argument('option_id', help='Option ID to regenerate')

    # regenerate meta-summary <id>
    regen_meta = regen_subparsers.add_parser('meta-summary', help='Regenerate meta summary')
    regen_meta.add_argument('option_id', help='Option ID to regenerate')

    # regenerate features --missing
    regen_features = regen_subparsers.add_parser('features', help='Regenerate all features')
    regen_features.add_argument('--missing', action='store_true', help='Only missing descriptions')
    regen_features.add_argument('--dry-run', action='store_true', help='Show what would be done')

    # regenerate options --missing
    regen_options = regen_subparsers.add_parser('options', help='Regenerate all options')
    regen_options.add_argument('--missing', action='store_true', help='Only missing descriptions')
    regen_options.add_argument('--dry-run', action='store_true', help='Show what would be done')

    # regenerate meta-summaries --all
    regen_metas = regen_subparsers.add_parser('meta-summaries', help='Regenerate all meta summaries')
    regen_metas.add_argument('--all', action='store_true', help='Regenerate all')
    regen_metas.add_argument('--dry-run', action='store_true', help='Show what would be done')

    # General command
    general_parser = subparsers.add_parser('general', help='Manage general-tagged content')
    general_subparsers = general_parser.add_subparsers(dest='general_action', help='Action')

    # general list
    general_subparsers.add_parser('list', help='List content tagged as general')

    # general show <id>
    general_show = general_subparsers.add_parser('show', help='Show details of an item')
    general_show.add_argument('content_id', help='Content ID to show')

    # general assign <id> --feature/--option/--new-feature/--new-option
    general_assign = general_subparsers.add_parser('assign', help='Assign to feature/option')
    general_assign.add_argument('content_id', help='Content ID to assign')
    general_assign.add_argument('--feature', help='Assign to existing feature')
    general_assign.add_argument('--option', help='Assign to existing option')
    general_assign.add_argument('--new-feature', nargs=2, metavar=('ID', 'NAME'), help='Create new feature')
    general_assign.add_argument('--new-option', nargs=3, metavar=('FEATURE_ID', 'OPTION_ID', 'NAME'), help='Create new option')

    # general triage
    general_triage = general_subparsers.add_parser('triage', help='Interactive triage')
    general_triage.add_argument('--auto-high', action='store_true', help='Auto-assign >80% confidence')
    general_triage.add_argument('--days', type=int, help='Only items from last N days')
    general_triage.add_argument('--export', metavar='FILE', help='Export suggestions to CSV')

    return parser


def main(args: Optional[list] = None) -> int:
    """Main entry point for CLI.

    Args:
        args: Command line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 for success).
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 1

    # Command handlers will be added in subsequent tasks
    print(f"Command: {parsed.command}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
