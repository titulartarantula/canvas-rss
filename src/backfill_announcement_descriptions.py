#!/usr/bin/env python3
"""Regenerate announcement descriptions with longer 3-5 sentence format.

Usage:
    python src/backfill_announcement_descriptions.py
    python src/backfill_announcement_descriptions.py --dry-run
"""

import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from utils.database import Database
from processor.content_processor import ContentProcessor


def backfill_announcement_descriptions(dry_run: bool = False):
    db = Database()
    processor = ContentProcessor()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Get all announcements with their raw content
    cursor.execute("""
        SELECT fa.id, fa.h4_title, fa.description,
               fa.content_id, ci.url
        FROM feature_announcements fa
        JOIN content_items ci ON fa.content_id = ci.source_id
        ORDER BY fa.id
    """)
    announcements = [dict(row) for row in cursor.fetchall()]

    print(f"Found {len(announcements)} announcements to regenerate")

    count = 0
    for ann in announcements:
        try:
            # Use h4_title as context since raw_content may not be stored
            new_desc = processor.summarize_announcement_description(
                ann["h4_title"],
                ann["description"] or ann["h4_title"]
            )
            if new_desc:
                if not dry_run:
                    cursor.execute(
                        "UPDATE feature_announcements SET description = ? WHERE id = ?",
                        (new_desc, ann["id"])
                    )
                    conn.commit()
                count += 1
                print(f"  [{count}] {ann['h4_title']}: {new_desc[:80]}...")
            else:
                print(f"  [empty] {ann['h4_title']}")
        except Exception as e:
            print(f"  [error] {ann['h4_title']}: {e}")

    print(f"\nRegenerated {count}/{len(announcements)} descriptions")
    if dry_run:
        print("(dry run - no DB changes made)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    backfill_announcement_descriptions(dry_run=args.dry_run)
