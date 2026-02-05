"""Options API endpoint."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Literal

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["options"])


@router.get("/options")
def get_options(
    status: Optional[str] = Query(None, description="Filter by status (pending, preview, optional, default_optional, released)"),
    feature: Optional[str] = Query(None, description="Filter by feature_id"),
    sort: Optional[Literal["updated", "alphabetical", "beta_date", "production_date"]] = Query("updated", description="Sort order"),
):
    """Get list of all feature options with filtering and sorting."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Build query
        query = """
            SELECT
                fo.option_id,
                fo.feature_id,
                fo.canonical_name,
                fo.name,
                fo.description,
                fo.status,
                fo.beta_date,
                fo.production_date,
                fo.deprecation_date,
                fo.last_updated,
                f.name as feature_name
            FROM feature_options fo
            JOIN features f ON fo.feature_id = f.feature_id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND fo.status = ?"
            params.append(status)

        if feature:
            query += " AND fo.feature_id = ?"
            params.append(feature)

        # Sort order
        if sort == "alphabetical":
            query += " ORDER BY fo.name"
        elif sort == "beta_date":
            query += " ORDER BY fo.beta_date IS NULL, fo.beta_date ASC, fo.name"
        elif sort == "production_date":
            query += " ORDER BY fo.production_date IS NULL, fo.production_date ASC, fo.name"
        else:  # updated (default)
            query += " ORDER BY fo.last_updated DESC NULLS LAST, fo.name"

        cursor.execute(query, params)
        options = rows_to_list(cursor.fetchall())

        return {"options": options}


@router.get("/options/{option_id}")
def get_option_detail(option_id: str):
    """Get detailed information about a specific feature option."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get option
        cursor.execute("""
            SELECT
                fo.*,
                f.name as feature_name,
                f.description as feature_description
            FROM feature_options fo
            JOIN features f ON fo.feature_id = f.feature_id
            WHERE fo.option_id = ?
        """, (option_id,))
        option = row_to_dict(cursor.fetchone())

        if not option:
            raise HTTPException(status_code=404, detail="Feature option not found")

        # Structure the response
        result = {
            "option_id": option["option_id"],
            "canonical_name": option["canonical_name"],
            "name": option["name"],
            "description": option["description"],
            "meta_summary": option["meta_summary"],
            "status": option["status"],
            "beta_date": option["beta_date"],
            "production_date": option["production_date"],
            "deprecation_date": option["deprecation_date"],
            "first_seen": option["first_seen"],
            "last_seen": option["last_seen"],
            "user_group_url": option["user_group_url"],
            "feature": {
                "feature_id": option["feature_id"],
                "name": option["feature_name"],
                "description": option["feature_description"],
            },
            "configuration": {
                "config_level": option["config_level"],
                "default_state": option["default_state"],
            },
        }

        # Get announcements
        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.section, fa.category,
                fa.description, fa.implications, fa.announced_at,
                fa.enable_location_account, fa.enable_location_course,
                fa.subaccount_config, fa.permissions, fa.affected_areas,
                fa.affects_ui,
                ci.title as release_title, ci.url as release_url
            FROM feature_announcements fa
            JOIN content_items ci ON fa.content_id = ci.source_id
            WHERE fa.option_id = ?
            ORDER BY fa.announced_at DESC
        """, (option_id,))
        result["announcements"] = rows_to_list(cursor.fetchall())

        # Get configuration from most recent announcement
        if result["announcements"]:
            latest = result["announcements"][0]
            result["configuration"].update({
                "enable_location_account": latest["enable_location_account"],
                "enable_location_course": latest["enable_location_course"],
                "subaccount_config": latest["subaccount_config"],
                "permissions": latest["permissions"],
                "affected_areas": latest["affected_areas"],
                "affects_ui": latest["affects_ui"],
            })

        # Get community posts
        cursor.execute("""
            SELECT
                ci.source_id, ci.url, ci.title, ci.content_type,
                ci.summary, ci.first_posted,
                cfr.mention_type
            FROM content_feature_refs cfr
            JOIN content_items ci ON cfr.content_id = ci.source_id
            WHERE cfr.option_id = ?
            AND ci.content_type IN ('blog', 'question')
            ORDER BY ci.first_posted DESC
            LIMIT 10
        """, (option_id,))
        result["community_posts"] = rows_to_list(cursor.fetchall())

        return result
