"""Search API endpoint."""
from fastapi import APIRouter, Query

from src.api.database import get_db, rows_to_list

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def search(q: str = Query("", description="Search query")):
    """Search across features, options, and content."""
    if not q or len(q.strip()) < 2:
        return {"features": [], "options": [], "content": []}

    search_term = f"%{q}%"

    with get_db() as conn:
        cursor = conn.cursor()

        # Search features
        cursor.execute("""
            SELECT feature_id, name, description, status
            FROM features
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY name
            LIMIT 10
        """, (search_term, search_term))
        features = rows_to_list(cursor.fetchall())

        # Search options
        cursor.execute("""
            SELECT
                fo.option_id, fo.canonical_name, fo.name, fo.description,
                fo.status, fo.feature_id,
                f.name as feature_name
            FROM feature_options fo
            JOIN features f ON fo.feature_id = f.feature_id
            WHERE fo.name LIKE ? OR fo.canonical_name LIKE ? OR fo.description LIKE ?
            ORDER BY fo.name
            LIMIT 10
        """, (search_term, search_term, search_term))
        options = rows_to_list(cursor.fetchall())

        # Search content (release notes, blogs, Q&A)
        cursor.execute("""
            SELECT source_id, url, title, content_type, summary, first_posted
            FROM content_items
            WHERE title LIKE ? OR summary LIKE ?
            ORDER BY first_posted DESC
            LIMIT 10
        """, (search_term, search_term))
        content = rows_to_list(cursor.fetchall())

        return {
            "features": features,
            "options": options,
            "content": content,
        }
