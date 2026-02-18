"""Features API endpoint."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from src.api.database import get_db, row_to_dict, rows_to_list, OPTION_STATUS_SQL, SETTING_STATUS_SQL

router = APIRouter(prefix="/api", tags=["features"])


# Category mapping for filtering
FEATURE_CATEGORIES = {
    "core": ["announcements", "assignments", "discussions", "files", "modules", "pages", "syllabus"],
    "grading": ["gradebook", "speedgrader", "rubrics", "outcomes", "mastery_paths", "peer_reviews", "roll_call_attendance"],
    "quizzes": ["classic_quizzes", "new_quizzes"],
    "collaboration": ["collaborations", "conferences", "groups", "chat"],
    "communication": ["inbox", "calendar", "notifications"],
    "ui": ["dashboard", "global_navigation", "profile_settings", "rich_content_editor"],
    "portfolio": ["eportfolios", "student_eportfolios"],
    "analytics": ["canvas_analytics", "canvas_data_services"],
    "addons": ["canvas_catalog", "canvas_studio", "canvas_commons", "student_pathways", "mastery_connect", "parchment_badges"],
    "mobile": ["canvas_mobile"],
    "admin": ["course_import", "blueprint_courses", "sis_import", "external_apps_lti", "canvas_apps", "developer_keys", "reports", "api", "account_settings", "themes_branding", "authentication"],
}


@router.get("/features")
def get_features(category: Optional[str] = Query(None, description="Filter by category")):
    """Get list of all features with option counts and status summary."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Build query with optional category filter
        query = f"""
            SELECT
                f.feature_id,
                f.name,
                f.description,
                f.status,
                COUNT(fo.option_id) as option_count,
                (SELECT COUNT(*) FROM feature_settings fs WHERE fs.feature_id = f.feature_id) as setting_count,
                SUM(CASE WHEN ({OPTION_STATUS_SQL}) = 'preview' THEN 1 ELSE 0 END) as preview_count,
                SUM(CASE WHEN ({OPTION_STATUS_SQL}) = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN ({OPTION_STATUS_SQL}) = 'optional' THEN 1 ELSE 0 END) as optional_count,
                SUM(CASE WHEN ({OPTION_STATUS_SQL}) = 'beta' THEN 1 ELSE 0 END) as beta_count,
                SUM(CASE WHEN ({OPTION_STATUS_SQL}) = 'delayed' THEN 1 ELSE 0 END) as delayed_count
            FROM features f
            LEFT JOIN feature_options fo ON f.feature_id = fo.feature_id
        """

        params = []
        if category and category in FEATURE_CATEGORIES:
            placeholders = ",".join("?" * len(FEATURE_CATEGORIES[category]))
            query += f" WHERE f.feature_id IN ({placeholders})"
            params = FEATURE_CATEGORIES[category]

        query += " GROUP BY f.feature_id ORDER BY f.name"

        cursor.execute(query, params)
        features = rows_to_list(cursor.fetchall())

        # Add status summary to each feature
        for feature in features:
            summaries = []
            if feature.get("delayed_count"):
                summaries.append(f"{feature['delayed_count']} delayed")
            if feature["preview_count"]:
                summaries.append(f"{feature['preview_count']} in preview")
            if feature.get("beta_count"):
                summaries.append(f"{feature['beta_count']} in beta")
            if feature["pending_count"]:
                summaries.append(f"{feature['pending_count']} pending")
            if feature["optional_count"]:
                summaries.append(f"{feature['optional_count']} optional")
            if not summaries and feature["option_count"]:
                summaries.append("all stable")
            feature["status_summary"] = ", ".join(summaries) if summaries else ""

        return {"features": features}


@router.get("/features/{feature_id}")
def get_feature_detail(feature_id: str):
    """Get detailed information about a specific feature."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get feature
        cursor.execute("""
            SELECT feature_id, name, description, status
            FROM features
            WHERE feature_id = ?
        """, (feature_id,))
        feature = row_to_dict(cursor.fetchone())

        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")

        # Get associated options
        cursor.execute(f"""
            SELECT
                fo.option_id, fo.canonical_name, fo.name, fo.description, fo.meta_summary,
                {OPTION_STATUS_SQL} as status,
                fo.beta_date, fo.production_date, fo.deprecation_date,
                fo.config_level, fo.default_state, fo.user_group_url,
                fo.first_seen, fo.last_seen
            FROM feature_options fo
            WHERE fo.feature_id = ?
            ORDER BY fo.name
        """, (feature_id,))
        feature["options"] = rows_to_list(cursor.fetchall())

        # Get associated settings
        cursor.execute(f"""
            SELECT
                fs.setting_id, fs.name, fs.description, fs.meta_summary,
                {SETTING_STATUS_SQL} as status,
                fs.beta_date, fs.production_date,
                fs.affected_areas, fs.affects_ui,
                fs.first_seen, fs.last_seen
            FROM feature_settings fs
            WHERE fs.feature_id = ?
            ORDER BY fs.name
        """, (feature_id,))
        feature["settings"] = rows_to_list(cursor.fetchall())

        # Get recent announcements
        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.section, fa.category,
                fa.description, fa.announced_at,
                ci.title as release_title, ci.url as release_url
            FROM feature_announcements fa
            JOIN content_items ci ON fa.content_id = ci.source_id
            WHERE fa.feature_id = ?
            ORDER BY fa.announced_at DESC
            LIMIT 10
        """, (feature_id,))
        feature["announcements"] = rows_to_list(cursor.fetchall())

        # Get related community posts
        cursor.execute("""
            SELECT
                ci.source_id, ci.url, ci.title, ci.content_type,
                ci.summary, ci.first_posted,
                cfr.mention_type
            FROM content_feature_refs cfr
            JOIN content_items ci ON cfr.content_id = ci.source_id
            WHERE cfr.feature_id = ?
            AND ci.content_type IN ('blog', 'question')
            ORDER BY ci.first_posted DESC
            LIMIT 10
        """, (feature_id,))
        feature["community_posts"] = rows_to_list(cursor.fetchall())

        return feature
