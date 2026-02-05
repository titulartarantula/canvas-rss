"""Dashboard API endpoint."""
from fastapi import APIRouter, Query
from typing import Optional

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(date: Optional[str] = Query(None, description="Filter by publish date (YYYY-MM-DD)")):
    """
    Get dashboard data including current release/deploy notes,
    upcoming changes, and recent activity.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get release note (most recent or by date)
        if date:
            cursor.execute("""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'release_note'
                AND date(first_posted) = ?
                ORDER BY first_posted DESC
                LIMIT 1
            """, (date,))
        else:
            cursor.execute("""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'release_note'
                ORDER BY first_posted DESC
                LIMIT 1
            """)
        release_note = row_to_dict(cursor.fetchone())

        # Get deploy note (most recent or by date)
        if date:
            cursor.execute("""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'deploy_note'
                AND date(first_posted) = ?
                ORDER BY first_posted DESC
                LIMIT 1
            """, (date,))
        else:
            cursor.execute("""
                SELECT source_id, url, title, content_type, summary, first_posted, published_date
                FROM content_items
                WHERE content_type = 'deploy_note'
                ORDER BY first_posted DESC
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

        # Get recent activity (blog + Q&A posts, last 7 days)
        cursor.execute("""
            SELECT source_id, url, title, content_type, summary, first_posted
            FROM content_items
            WHERE content_type IN ('blog', 'question')
            ORDER BY first_posted DESC
            LIMIT 10
        """)
        recent_activity = rows_to_list(cursor.fetchall())

        # Get feature announcements for release note
        announcements = []
        if release_note:
            cursor.execute("""
                SELECT
                    fa.h4_title,
                    fa.section,
                    fa.category,
                    fa.description,
                    fa.option_id,
                    fo.beta_date,
                    fo.production_date,
                    fo.status as option_status
                FROM feature_announcements fa
                LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
                WHERE fa.content_id = ?
                ORDER BY fa.section, fa.category
            """, (release_note["source_id"],))
            announcements = rows_to_list(cursor.fetchall())

        if release_note:
            release_note["announcements"] = announcements

        return {
            "release_note": release_note,
            "deploy_note": deploy_note,
            "upcoming_changes": upcoming_changes,
            "recent_activity": recent_activity,
        }
