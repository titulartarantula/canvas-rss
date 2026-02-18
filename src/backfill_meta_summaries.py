#!/usr/bin/env python3
"""Regenerate meta_summaries for all feature options and settings.

Clears existing meta_summaries and regenerates them using the improved
prompt that focuses on the named entity and avoids markdown formatting.

Usage:
    python src/backfill_meta_summaries.py
    # Or dry-run (no DB writes):
    python src/backfill_meta_summaries.py --dry-run
"""

import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from utils.database import Database
from processor.content_processor import ContentProcessor


def backfill_meta_summaries(dry_run: bool = False):
    db = Database()
    processor = ContentProcessor()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Phase 1: Feature Options
    cursor.execute("""
        SELECT fo.option_id, fo.canonical_name, fo.name, fo.implementation_status,
               f.name as feature_name
        FROM feature_options fo
        JOIN features f ON fo.feature_id = f.feature_id
        ORDER BY f.name, fo.name
    """)
    options = [dict(row) for row in cursor.fetchall()]

    print(f"--- Feature Options ({len(options)} total) ---")
    option_count = 0
    for opt in options:
        display_name = opt["canonical_name"] or opt["name"]
        feature_name = opt["feature_name"]

        content = db.get_latest_content_for_option(opt["option_id"], limit=5)
        content_summaries = [
            {
                'date': c.get('first_posted', 'Unknown')[:10] if c.get('first_posted') else 'Unknown',
                'title': c.get('title', ''),
                'description': c.get('announcement_description', ''),
            }
            for c in content
        ]

        if not content_summaries:
            print(f"  [skip] {display_name}: no content to summarize")
            continue

        try:
            summary = processor.generate_meta_summary(
                option_name=display_name,
                feature_name=feature_name,
                implementation_status=opt.get("implementation_status", ""),
                content_summaries=content_summaries,
                entity_type="option",
            )
            if summary:
                if not dry_run:
                    db.update_feature_option_meta_summary(opt["option_id"], summary)
                option_count += 1
                print(f"  [{option_count}] {display_name}: {summary[:80]}...")
            else:
                print(f"  [empty] {display_name}: LLM returned empty")
        except Exception as e:
            print(f"  [error] {display_name}: {e}")

    print(f"\nGenerated {option_count} option meta_summaries.")

    # Phase 2: Feature Settings
    cursor.execute("""
        SELECT fs.setting_id, fs.name, fs.implementation_status,
               f.name as feature_name
        FROM feature_settings fs
        JOIN features f ON fs.feature_id = f.feature_id
        ORDER BY f.name, fs.name
    """)
    settings = [dict(row) for row in cursor.fetchall()]

    print(f"\n--- Feature Settings ({len(settings)} total) ---")
    setting_count = 0
    for setting in settings:
        setting_name = setting["name"]
        feature_name = setting["feature_name"]

        content = db.get_latest_content_for_setting(setting["setting_id"], limit=5)
        content_summaries = [
            {
                'date': c.get('first_posted', 'Unknown')[:10] if c.get('first_posted') else 'Unknown',
                'title': c.get('title', ''),
                'description': c.get('announcement_description', ''),
            }
            for c in content
        ]

        if not content_summaries:
            print(f"  [skip] {setting_name}: no content to summarize")
            continue

        try:
            summary = processor.generate_meta_summary(
                option_name=setting_name,
                feature_name=feature_name,
                implementation_status=setting.get("implementation_status", ""),
                content_summaries=content_summaries,
                entity_type="setting",
            )
            if summary:
                if not dry_run:
                    db.update_feature_setting_meta_summary(setting["setting_id"], summary)
                setting_count += 1
                print(f"  [{setting_count}/{len(settings)}] {setting_name}: {summary[:80]}...")
            else:
                print(f"  [empty] {setting_name}: LLM returned empty")
        except Exception as e:
            print(f"  [error] {setting_name}: {e}")

    print(f"\nGenerated {setting_count} setting meta_summaries.")
    print(f"\n=== Summary ===")
    print(f"Options:  {option_count}")
    print(f"Settings: {setting_count}")
    if dry_run:
        print("(dry run - no DB changes made)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate meta_summaries")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()
    backfill_meta_summaries(dry_run=args.dry_run)
