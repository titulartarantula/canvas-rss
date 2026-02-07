"""Settings API endpoint."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Literal

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
def get_settings(
    status: Optional[str] = Query(None, description="Filter by status (active, deprecated)"),
    feature: Optional[str] = Query(None, description="Filter by feature_id"),
    sort: Optional[Literal["updated", "alphabetical", "beta_date", "production_date"]] = Query("updated", description="Sort order"),
):
    """Get list of all feature settings with filtering and sorting."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
                fs.setting_id,
                fs.feature_id,
                fs.name,
                fs.description,
                fs.status,
                fs.beta_date,
                fs.production_date,
                fs.affected_areas,
                fs.affects_ui,
                fs.last_updated,
                f.name as feature_name
            FROM feature_settings fs
            JOIN features f ON fs.feature_id = f.feature_id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND fs.status = ?"
            params.append(status)

        if feature:
            query += " AND fs.feature_id = ?"
            params.append(feature)

        if sort == "alphabetical":
            query += " ORDER BY fs.name"
        elif sort == "beta_date":
            query += " ORDER BY fs.beta_date IS NULL, fs.beta_date ASC, fs.name"
        elif sort == "production_date":
            query += " ORDER BY fs.production_date IS NULL, fs.production_date ASC, fs.name"
        else:
            query += " ORDER BY fs.last_updated DESC NULLS LAST, fs.name"

        cursor.execute(query, params)
        settings = rows_to_list(cursor.fetchall())

        return {"settings": settings}


@router.get("/settings/{setting_id}")
def get_setting_detail(setting_id: str):
    """Get detailed information about a specific feature setting."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                fs.*,
                f.name as feature_name,
                f.description as feature_description
            FROM feature_settings fs
            JOIN features f ON fs.feature_id = f.feature_id
            WHERE fs.setting_id = ?
        """, (setting_id,))
        setting = row_to_dict(cursor.fetchone())

        if not setting:
            raise HTTPException(status_code=404, detail="Feature setting not found")

        result = {
            "setting_id": setting["setting_id"],
            "name": setting["name"],
            "description": setting["description"],
            "meta_summary": setting["meta_summary"],
            "status": setting["status"],
            "beta_date": setting["beta_date"],
            "production_date": setting["production_date"],
            "affected_areas": setting["affected_areas"],
            "affects_ui": setting["affects_ui"],
            "affects_roles": setting["affects_roles"],
            "first_seen": setting["first_seen"],
            "last_seen": setting["last_seen"],
            "feature": {
                "feature_id": setting["feature_id"],
                "name": setting["feature_name"],
                "description": setting["feature_description"],
            },
        }

        # Get announcements
        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.section, fa.category,
                fa.description, fa.implications, fa.announced_at,
                fa.affected_areas, fa.affects_ui,
                ci.title as release_title, ci.url as release_url
            FROM feature_announcements fa
            JOIN content_items ci ON fa.content_id = ci.source_id
            WHERE fa.setting_id = ?
            ORDER BY fa.announced_at DESC
        """, (setting_id,))
        result["announcements"] = rows_to_list(cursor.fetchall())

        # Get community posts
        cursor.execute("""
            SELECT
                ci.source_id, ci.url, ci.title, ci.content_type,
                ci.summary, ci.first_posted,
                cfr.mention_type
            FROM content_feature_refs cfr
            JOIN content_items ci ON cfr.content_id = ci.source_id
            WHERE cfr.feature_setting_id = ?
            AND ci.content_type IN ('blog', 'question')
            ORDER BY ci.first_posted DESC
            LIMIT 10
        """, (setting_id,))
        result["community_posts"] = rows_to_list(cursor.fetchall())

        return result
