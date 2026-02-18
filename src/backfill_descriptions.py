#!/usr/bin/env python3
"""Generate canonical (glossary-style) descriptions for features, options, and settings.

This is a one-time backfill script. It clears existing description values
and regenerates them using Gemini's built-in Canvas LMS knowledge.

Usage:
    python src/backfill_descriptions.py
    # Or dry-run (no DB writes):
    python src/backfill_descriptions.py --dry-run
"""

import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from constants import CANVAS_FEATURES
from utils.database import Database
from processor.content_processor import ContentProcessor


def backfill_descriptions(dry_run: bool = False):
    db = Database()
    processor = ContentProcessor()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Phase 1: Clear existing descriptions
    if not dry_run:
        print("Clearing existing descriptions...")
        cursor.execute("UPDATE features SET description = NULL, llm_generated_at = NULL")
        cursor.execute("UPDATE feature_options SET description = NULL, llm_generated_at = NULL")
        cursor.execute("UPDATE feature_settings SET description = NULL, llm_generated_at = NULL")
        conn.commit()
        print("  Cleared.")

    # Phase 2: Generate feature descriptions
    print(f"\n--- Features ({len(CANVAS_FEATURES)} total) ---")
    feature_count = 0
    for feature_id, feature_name in CANVAS_FEATURES.items():
        # Check feature exists in DB
        cursor.execute("SELECT feature_id FROM features WHERE feature_id = ?", (feature_id,))
        if not cursor.fetchone():
            print(f"  [skip] {feature_name}: not in DB")
            continue

        try:
            desc = processor.generate_canonical_feature_description(feature_name)
            if desc:
                if not dry_run:
                    db.update_feature_description(feature_id, desc)
                feature_count += 1
                print(f"  [{feature_count}] {feature_name}: {desc[:80]}...")
            else:
                print(f"  [empty] {feature_name}: LLM returned empty")
        except Exception as e:
            print(f"  [error] {feature_name}: {e}")

    print(f"\nGenerated {feature_count} feature descriptions.")

    # Phase 3: Generate feature option descriptions
    cursor.execute("""
        SELECT fo.option_id, fo.canonical_name, fo.name, f.name as feature_name
        FROM feature_options fo
        JOIN features f ON fo.feature_id = f.feature_id
        ORDER BY f.name, fo.name
    """)
    options = [dict(row) for row in cursor.fetchall()]

    print(f"\n--- Feature Options ({len(options)} total) ---")
    option_count = 0
    for opt in options:
        display_name = opt["canonical_name"] or opt["name"]
        feature_name = opt["feature_name"]

        try:
            desc = processor.generate_canonical_option_description(display_name, feature_name)
            if desc:
                if not dry_run:
                    db.update_feature_option_description(opt["option_id"], desc)
                option_count += 1
                print(f"  [{option_count}] {display_name}: {desc[:80]}...")
            else:
                print(f"  [empty] {display_name}: LLM returned empty")
        except Exception as e:
            print(f"  [error] {display_name}: {e}")

    print(f"\nGenerated {option_count} option descriptions.")

    # Phase 4: Generate feature setting descriptions
    cursor.execute("""
        SELECT fs.setting_id, fs.name, f.name as feature_name
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

        try:
            desc = processor.generate_canonical_setting_description(setting_name, feature_name)
            if desc:
                if not dry_run:
                    db.update_feature_setting_description(setting["setting_id"], desc)
                setting_count += 1
                print(f"  [{setting_count}/{len(settings)}] {setting_name}: {desc[:80]}...")
            else:
                print(f"  [empty] {setting_name}: LLM returned empty")
        except Exception as e:
            print(f"  [error] {setting_name}: {e}")

    print(f"\nGenerated {setting_count} setting descriptions.")
    print(f"\n=== Summary ===")
    print(f"Features: {feature_count}")
    print(f"Options:  {option_count}")
    print(f"Settings: {setting_count}")
    if dry_run:
        print("(dry run — no DB changes made)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate canonical descriptions")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()
    backfill_descriptions(dry_run=args.dry_run)
