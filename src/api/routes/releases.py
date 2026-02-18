"""Releases archive API endpoint."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["releases"])

# Extract date from title pattern "Canvas ... Notes (YYYY-MM-DD)"
_TITLE_DATE_SQL = "substr(ci.title, instr(ci.title, '(') + 1, 10)"


@router.get("/releases")
def get_releases(
    type: Optional[str] = Query(None, description="Filter by type (release_note, deploy_note)"),
    year: Optional[int] = Query(None, ge=1900, le=2100, description="Filter by year"),
    search: Optional[str] = Query(None, description="Search in title"),
):
    """Get list of release and deploy notes."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = f"""
            SELECT
                ci.source_id,
                ci.url,
                ci.title,
                ci.content_type,
                ci.summary,
                ci.first_posted,
                ci.published_date,
                {_TITLE_DATE_SQL} as production_date,
                COUNT(fa.id) as announcement_count
            FROM content_items ci
            LEFT JOIN feature_announcements fa ON ci.source_id = fa.content_id
            WHERE ci.content_type IN ('release_note', 'deploy_note')
        """
        params = []

        if type:
            query += " AND ci.content_type = ?"
            params.append(type)

        if year:
            query += f" AND substr({_TITLE_DATE_SQL}, 1, 4) = ?"
            params.append(str(year))

        if search:
            query += " AND ci.title LIKE ?"
            params.append(f"%{search}%")

        query += f" GROUP BY ci.source_id ORDER BY {_TITLE_DATE_SQL} DESC"

        cursor.execute(query, params)
        releases = rows_to_list(cursor.fetchall())

        return {"releases": releases}


@router.get("/releases/{content_id}")
def get_release_detail(content_id: str):
    """Get full release or deploy note with all announcements."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get release/deploy note
        cursor.execute(f"""
            SELECT source_id, url, title, content_type, summary,
                   first_posted,
                   published_date,
                   {_TITLE_DATE_SQL} as production_date
            FROM content_items ci
            WHERE ci.source_id = ?
            AND ci.content_type IN ('release_note', 'deploy_note')
        """, (content_id,))
        release = row_to_dict(cursor.fetchone())

        if not release:
            raise HTTPException(status_code=404, detail="Release not found")

        # Get announcements grouped by section
        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.anchor_id, fa.section, fa.category,
                fa.description, fa.option_id,
                fa.enable_location_account, fa.enable_location_course,
                COALESCE(fa.beta_date, fo.beta_date) as beta_date,
                COALESCE(fa.production_date, fo.production_date) as production_date,
                fo.status as option_status
            FROM feature_announcements fa
            LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
            WHERE fa.content_id = ?
            ORDER BY fa.section, fa.category, fa.h4_title
        """, (content_id,))
        release["announcements"] = rows_to_list(cursor.fetchall())

        # Get upcoming changes
        cursor.execute("""
            SELECT change_date, description
            FROM upcoming_changes
            WHERE content_id = ?
            ORDER BY change_date ASC
        """, (content_id,))
        release["upcoming_changes"] = rows_to_list(cursor.fetchall())

        return release


@router.get("/announcements/{announcement_id}")
def get_announcement_detail(announcement_id: int):
    """Get a single feature announcement with parent release info."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.anchor_id, fa.section, fa.category,
                fa.description, fa.option_id, fa.setting_id,
                fa.enable_location_account, fa.enable_location_course,
                COALESCE(fa.beta_date, fo.beta_date) as beta_date,
                COALESCE(fa.production_date, fo.production_date) as production_date,
                fo.status as option_status,
                fa.content_id,
                ci.title as release_title,
                ci.url as release_url,
                ci.content_type as release_type,
                fo.canonical_name as option_name,
                fo.name as option_display_name,
                fs.name as setting_name
            FROM feature_announcements fa
            JOIN content_items ci ON fa.content_id = ci.source_id
            LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
            LEFT JOIN feature_settings fs ON fa.setting_id = fs.setting_id
            WHERE fa.id = ?
        """, (announcement_id,))
        announcement = row_to_dict(cursor.fetchone())

        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")

        return announcement
