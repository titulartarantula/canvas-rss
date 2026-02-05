"""Command-line interface for canvas-rss management."""

import argparse
import sys
from typing import Optional

from src.utils.database import Database
from src.processor.content_processor import ContentProcessor


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


def handle_regenerate_feature(feature_id: str, dry_run: bool = False) -> int:
    """Handle regenerate feature command.

    Args:
        feature_id: The feature ID to regenerate.
        dry_run: If True, don't actually update.

    Returns:
        Exit code.
    """
    db = Database()

    feature = db.get_feature(feature_id)
    if not feature:
        print(f"Error: Feature '{feature_id}' not found")
        return 1

    # Get recent content for context
    content = db.get_content_for_feature(feature_id)
    content_snippet = "\n".join([
        f"- {c.get('title', '')}: {c.get('content', '')[:200]}"
        for c in content[:5]
    ]) if content else "No recent content available."

    if dry_run:
        print(f"Would regenerate description for: {feature['name']}")
        print(f"Using context from {len(content)} content items")
        return 0

    processor = ContentProcessor()
    description = processor.summarize_feature_description(
        feature_name=feature['name'],
        content_snippet=content_snippet
    )

    if description:
        db.update_feature_description(feature_id, description)
        print(f"Updated description for {feature['name']}:")
        print(f"  {description}")
    else:
        print(f"Warning: Could not generate description (LLM unavailable?)")

    db.close()
    return 0


def handle_regenerate_option(option_id: str, dry_run: bool = False) -> int:
    """Handle regenerate option command."""
    db = Database()

    option = db.get_feature_option(option_id)
    if not option:
        print(f"Error: Option '{option_id}' not found")
        return 1

    feature = db.get_feature(option['feature_id'])
    feature_name = feature['name'] if feature else 'Unknown'

    content = db.get_latest_content_for_option(option_id, limit=3)
    raw_content = "\n".join([c.get('raw_content', c.get('content', ''))[:500] for c in content])

    if dry_run:
        print(f"Would regenerate description for: {option['name']}")
        return 0

    processor = ContentProcessor()
    description = processor.summarize_feature_option_description(
        option_name=option['name'],
        feature_name=feature_name,
        raw_content=raw_content or "Feature option for " + option['name']
    )

    if description:
        db.update_feature_option_description(option_id, description)
        print(f"Updated description for {option['name']}:")
        print(f"  {description}")

    db.close()
    return 0


def handle_regenerate_meta_summary(option_id: str, dry_run: bool = False) -> int:
    """Handle regenerate meta-summary command."""
    db = Database()

    option = db.get_feature_option(option_id)
    if not option:
        print(f"Error: Option '{option_id}' not found")
        return 1

    feature = db.get_feature(option['feature_id'])
    feature_name = feature['name'] if feature else 'Unknown'

    content = db.get_latest_content_for_option(option_id, limit=5)
    content_summaries = [
        {
            'date': c.get('first_posted', 'Unknown')[:10] if c.get('first_posted') else 'Unknown',
            'title': c.get('title', ''),
            'description': c.get('announcement_description', ''),
            'implications': c.get('implications', '')
        }
        for c in content
    ]

    if dry_run:
        print(f"Would regenerate meta_summary for: {option['name']}")
        print(f"Using {len(content_summaries)} content items")
        return 0

    processor = ContentProcessor()
    meta_summary = processor.generate_meta_summary(
        option_name=option['name'],
        feature_name=feature_name,
        implementation_status=option.get('implementation_status', ''),
        content_summaries=content_summaries
    )

    if meta_summary:
        db.update_feature_option_meta_summary(option_id, meta_summary)
        print(f"Updated meta_summary for {option['name']}:")
        print(f"  {meta_summary}")

    db.close()
    return 0


def handle_regenerate_features(missing_only: bool = False, dry_run: bool = False) -> int:
    """Handle regenerate features command."""
    db = Database()

    if missing_only:
        features = db.get_features_missing_description()
    else:
        features = db.get_all_features()

    if dry_run:
        print(f"Would regenerate {len(features)} features:")
        for f in features:
            print(f"  - {f['feature_id']}: {f['name']}")
        return 0

    processor = ContentProcessor()
    for f in features:
        content = db.get_content_for_feature(f['feature_id'])
        content_snippet = "\n".join([
            f"- {c.get('title', '')}: {c.get('content', '')[:200]}"
            for c in content[:5]
        ]) if content else ""

        description = processor.summarize_feature_description(
            feature_name=f['name'],
            content_snippet=content_snippet or f"The {f['name']} feature in Canvas LMS."
        )

        if description:
            db.update_feature_description(f['feature_id'], description)
            print(f"Updated: {f['name']}")

    db.close()
    return 0


def handle_regenerate_options(missing_only: bool = False, dry_run: bool = False) -> int:
    """Handle regenerate options command."""
    db = Database()

    if missing_only:
        options = db.get_feature_options_missing_description()
    else:
        options = db.get_all_feature_options()

    if dry_run:
        print(f"Would regenerate {len(options)} options:")
        for o in options:
            print(f"  - {o['option_id']}: {o['name']}")
        return 0

    processor = ContentProcessor()
    for o in options:
        feature = db.get_feature(o['feature_id'])
        feature_name = feature['name'] if feature else 'Unknown'

        content = db.get_latest_content_for_option(o['option_id'], limit=3)
        raw_content = "\n".join([c.get('raw_content', '')[:500] for c in content])

        description = processor.summarize_feature_option_description(
            option_name=o['name'],
            feature_name=feature_name,
            raw_content=raw_content or f"Feature option: {o['name']}"
        )

        if description:
            db.update_feature_option_description(o['option_id'], description)
            print(f"Updated: {o['name']}")

    db.close()
    return 0


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

    if parsed.command == 'regenerate':
        if parsed.regen_type == 'feature':
            return handle_regenerate_feature(parsed.feature_id)
        elif parsed.regen_type == 'option':
            return handle_regenerate_option(parsed.option_id)
        elif parsed.regen_type == 'meta-summary':
            return handle_regenerate_meta_summary(parsed.option_id)
        elif parsed.regen_type == 'features':
            return handle_regenerate_features(
                missing_only=parsed.missing,
                dry_run=parsed.dry_run
            )
        elif parsed.regen_type == 'options':
            return handle_regenerate_options(
                missing_only=parsed.missing,
                dry_run=parsed.dry_run
            )
        print(f"Regenerate {parsed.regen_type} not yet implemented")
        return 1

    # Command handlers will be added in subsequent tasks
    print(f"Command: {parsed.command}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
