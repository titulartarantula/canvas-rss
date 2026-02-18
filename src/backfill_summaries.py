#!/usr/bin/env python3
"""Backfill LLM-generated descriptions for existing feature announcements.

Usage:
    python src/backfill_summaries.py
    # Or from Docker:
    docker exec canvas-rss python src/backfill_summaries.py
"""

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.database import Database
from processor.content_processor import ContentProcessor


def backfill():
    db = Database()
    processor = ContentProcessor()

    conn = db._get_connection()
    cursor = conn.cursor()

    # Find announcements with NULL descriptions
    cursor.execute("""
        SELECT id, content_id, anchor_id, h4_title, raw_content, category
        FROM feature_announcements
        WHERE description IS NULL
        ORDER BY id
    """)
    rows = cursor.fetchall()

    total = len(rows)
    if total == 0:
        print("No announcements need backfilling.")
        return

    print(f"Found {total} announcements with NULL descriptions.")
    updated = 0

    for row in rows:
        ann = dict(row)
        h4_title = ann["h4_title"]
        raw_content = ann["raw_content"] or ""
        category = ann["category"] or "Unknown"

        try:
            description = processor.summarize_announcement_description(
                h4_title=h4_title,
                raw_content=raw_content,
            )

            if description:
                db.update_announcement_summary(
                    content_id=ann["content_id"],
                    anchor_id=ann["anchor_id"],
                    description=description,
                )
                updated += 1
                print(f"  [{updated}/{total}] {h4_title}: {description[:60]}...")
            else:
                print(f"  [skip] {h4_title}: LLM returned empty")

        except Exception as e:
            print(f"  [error] {h4_title}: {e}")

    print(f"\nDone. Updated {updated}/{total} announcements.")

    # Propagate descriptions to parent feature_options and feature_settings
    propagate_descriptions(db)


def propagate_descriptions(db: Database):
    """Copy announcement descriptions to parent feature_options/settings that lack them."""
    conn = db._get_connection()
    cursor = conn.cursor()

    # Propagate to feature_options: use most recent announcement's description
    cursor.execute("""
        SELECT fo.option_id, fa.description
        FROM feature_options fo
        JOIN feature_announcements fa ON fa.option_id = fo.option_id
        WHERE (fo.description IS NULL OR fo.description = '')
          AND fa.description IS NOT NULL AND fa.description != ''
        ORDER BY fo.option_id, fa.announced_at DESC
    """)
    rows = cursor.fetchall()
    updated_options = set()
    for row in rows:
        opt_id = row["option_id"]
        if opt_id not in updated_options:
            db.update_feature_option_description(opt_id, row["description"])
            updated_options.add(opt_id)
            print(f"  [option] {opt_id}: {row['description'][:60]}...")
    print(f"Propagated descriptions to {len(updated_options)} feature options.")

    # Propagate to feature_settings: use most recent announcement's description
    cursor.execute("""
        SELECT fs.setting_id, fa.description
        FROM feature_settings fs
        JOIN feature_announcements fa ON fa.setting_id = fs.setting_id
        WHERE (fs.description IS NULL OR fs.description = '')
          AND fa.description IS NOT NULL AND fa.description != ''
        ORDER BY fs.setting_id, fa.announced_at DESC
    """)
    rows = cursor.fetchall()
    updated_settings = set()
    for row in rows:
        set_id = row["setting_id"]
        if set_id not in updated_settings:
            db.update_feature_setting_description(set_id, row["description"])
            updated_settings.add(set_id)
            print(f"  [setting] {set_id}: {row['description'][:60]}...")
    print(f"Propagated descriptions to {len(updated_settings)} feature settings.")


if __name__ == "__main__":
    backfill()
