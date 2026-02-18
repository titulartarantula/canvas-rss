"""Options API endpoint."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Literal

from src.api.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api", tags=["options"])


@router.get("/options")
def get_options(
    lifecycle_stage: Optional[str] = Query(None, description="Filter by lifecycle_stage (preview, stable, pending)"),
    feature: Optional[str] = Query(None, description="Filter by feature_id"),
    sort: Optional[Literal["updated", "alphabetical", "beta_date", "production_date"]] = Query("updated", description="Sort order"),
):
    """Get list of all feature options with filtering and sorting."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
                fo.option_id,
                fo.feature_id,
                fo.canonical_name,
                fo.name,
                fo.description,
                fo.lifecycle_stage,
                fo.prod_account_state,
                fo.prod_course_state,
                fo.beta_account_state,
                fo.beta_course_state,
                fo.beta_date,
                fo.production_date,
                fo.deprecation_date,
                fo.user_group_url,
                fo.doc_url,
                fo.source,
                fo.last_updated,
                f.name as feature_name
            FROM feature_options fo
            JOIN features f ON fo.feature_id = f.feature_id
            WHERE 1=1
        """
        params = []

        if lifecycle_stage:
            query += " AND fo.lifecycle_stage = ?"
            params.append(lifecycle_stage)

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

        # Get option with all new columns
        cursor.execute("""
            SELECT
                fo.option_id, fo.feature_id, fo.canonical_name, fo.name,
                fo.description, fo.meta_summary,
                fo.lifecycle_stage,
                fo.prod_account_state, fo.prod_course_state,
                fo.beta_account_state, fo.beta_course_state,
                fo.beta_date, fo.production_date, fo.deprecation_date,
                fo.user_group_url, fo.doc_url, fo.source,
                fo.first_seen, fo.last_seen,
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
            "lifecycle_stage": option["lifecycle_stage"],
            "beta_date": option["beta_date"],
            "production_date": option["production_date"],
            "deprecation_date": option["deprecation_date"],
            "first_seen": option["first_seen"],
            "last_seen": option["last_seen"],
            "user_group_url": option["user_group_url"],
            "doc_url": option["doc_url"],
            "source": option["source"],
            "feature": {
                "feature_id": option["feature_id"],
                "name": option["feature_name"],
                "description": option["feature_description"],
            },
            "configuration": {
                "prod_account_state": option["prod_account_state"],
                "prod_course_state": option["prod_course_state"],
                "beta_account_state": option["beta_account_state"],
                "beta_course_state": option["beta_course_state"],
            },
        }

        # Get announcements
        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.section, fa.category,
                fa.description, fa.announced_at,
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

        # Get community posts
        cursor.execute("""
            SELECT
                ci.source_id, ci.url, ci.title, ci.content_type,
                ci.summary, ci.first_posted,
                cfr.mention_type
            FROM content_feature_refs cfr
            JOIN content_items ci ON cfr.content_id = ci.source_id
            WHERE cfr.feature_option_id = ?
            AND ci.content_type IN ('blog', 'question')
            ORDER BY ci.first_posted DESC
            LIMIT 10
        """, (option_id,))
        result["community_posts"] = rows_to_list(cursor.fetchall())

        return result
