"""Dashboard API endpoint."""
import re
from fastapi import APIRouter, Query
from typing import Optional

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["dashboard"])

# Titles follow: "Canvas Release Notes (YYYY-MM-DD)" or "Canvas Deploy Notes (YYYY-MM-DD)"
# Extract the date portion for reliable chronological ordering
_TITLE_DATE_SQL = """
    substr(title, instr(title, '(') + 1, 10)
"""


def _get_announcements(cursor, content_id: str) -> list:
    """Get feature announcements for a content item."""
    cursor.execute("""
        SELECT
            fa.h4_title,
            fa.section,
            fa.category,
            fa.description,
            fa.implications,
            fa.option_id,
            COALESCE(fa.beta_date, fo.beta_date) as beta_date,
            COALESCE(fa.production_date, fo.production_date) as production_date,
            fo.status as option_status
        FROM feature_announcements fa
        LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
        WHERE fa.content_id = ?
        ORDER BY fa.section, fa.category
    """, (content_id,))
    return rows_to_list(cursor.fetchall())


@router.get("/dashboard")
def get_dashboard(date: Optional[str] = Query(None, description="Filter by publish date (YYYY-MM-DD)")):
    """
    Get dashboard data including current release/deploy notes,
    upcoming changes, and recent activity.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get release note — order by date extracted from title for correct chronological order
        if date:
            cursor.execute(f"""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'release_note'
                AND {_TITLE_DATE_SQL} = ?
                ORDER BY {_TITLE_DATE_SQL} DESC
                LIMIT 1
            """, (date,))
        else:
            cursor.execute(f"""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'release_note'
                ORDER BY {_TITLE_DATE_SQL} DESC
                LIMIT 1
            """)
        release_note = row_to_dict(cursor.fetchone())

        # Get deploy note
        if date:
            cursor.execute(f"""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'deploy_note'
                AND {_TITLE_DATE_SQL} = ?
                ORDER BY {_TITLE_DATE_SQL} DESC
                LIMIT 1
            """, (date,))
        else:
            cursor.execute(f"""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'deploy_note'
                ORDER BY {_TITLE_DATE_SQL} DESC
                LIMIT 1
            """)
        deploy_note = row_to_dict(cursor.fetchone())

        # Get upcoming changes (from most recent release note)
        upcoming_changes = []
        if release_note:
            cursor.execute("""
                SELECT change_date, description
                FROM upcoming_changes
                WHERE content_id = ?
                ORDER BY change_date ASC
            """, (release_note["source_id"],))
            upcoming_changes = rows_to_list(cursor.fetchall())

        # Get recent activity (blog + Q&A posts)
        cursor.execute("""
            SELECT source_id, url, title, content_type, summary, first_posted
            FROM content_items
            WHERE content_type IN ('blog', 'question')
            ORDER BY COALESCE(first_posted, published_date) DESC
            LIMIT 10
        """)
        recent_activity = rows_to_list(cursor.fetchall())

        # Get feature announcements for both release and deploy notes
        if release_note:
            release_note["announcements"] = _get_announcements(cursor, release_note["source_id"])

        if deploy_note:
            deploy_note["announcements"] = _get_announcements(cursor, deploy_note["source_id"])

        return {
            "release_note": release_note,
            "deploy_note": deploy_note,
            "upcoming_changes": upcoming_changes,
            "recent_activity": recent_activity,
        }
