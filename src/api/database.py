"""Database connection utilities for the API."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

# Default database path - can be overridden via environment variable
import os
DB_PATH = Path(os.getenv("DATABASE_PATH", "data/canvas_digest.db"))


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a dictionary."""
    return dict(row) if row else None


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    """Convert a list of sqlite3.Row to a list of dictionaries."""
    return [dict(row) for row in rows]


# --- Computed status SQL expressions ---
# Feature settings: status is derived from production_date/beta_date at query time.
# Explicit override statuses (delayed, deprecated) are preserved as-is.

def _computed_status(date_prefix: str, status_col: str, released_label: str = "released") -> str:
    """Build a CASE expression that computes status from dates.

    Used for feature_settings which still have a status column.
    Explicit lifecycle statuses are preserved as-is. Date-based computation
    only applies when the stored status is 'pending' (the default).

    Args:
        date_prefix: Table alias for production_date/beta_date columns (e.g. "fs").
        status_col: Fully-qualified status column (e.g. "fs.status").
        released_label: Label for the 'released' state ('active' for settings).
    """
    return f"""CASE
        WHEN {status_col} IN ('delayed', 'deprecated', 'preview', 'optional', 'default_on', 'default_optional', '{released_label}')
             THEN {status_col}
        WHEN {date_prefix}.production_date IS NOT NULL
             AND {date_prefix}.production_date <= date('now') THEN '{released_label}'
        WHEN {date_prefix}.beta_date IS NOT NULL
             AND {date_prefix}.beta_date <= date('now') THEN 'beta'
        ELSE 'pending'
    END"""


# Feature settings: fs.status → computed from fs.production_date / fs.beta_date
SETTING_STATUS_SQL = _computed_status("fs", "fs.status", "active")


def compute_availability(beta_date: str | None, production_date: str | None) -> str:
    """Compute availability label from dates."""
    from datetime import date
    today = date.today().isoformat()
    if production_date and production_date <= today:
        return 'in_production'
    if beta_date and beta_date <= today:
        if production_date:
            return 'upcoming_production'
        return 'in_beta'
    if beta_date:
        return 'upcoming_beta'
    return 'no_dates'


def announcement_status_sql(fa_alias: str = "fa", fs_alias: str = "fs", fo_alias: str = "fo", **_kwargs) -> str:
    """Compute announcement category: setting or preview.

    Announcements linked to a known feature (option or setting) are
    categorised as 'feature_setting'. Only truly unlinked announcements
    are 'feature_preview'.

    Categories:
    - 'feature_setting': linked to a feature_settings or feature_options record
    - 'feature_preview': not linked to any known feature
    """
    return f"""CASE
        WHEN {fa_alias}.setting_id IS NOT NULL AND {fs_alias}.setting_id IS NOT NULL
             THEN 'feature_setting'
        WHEN {fa_alias}.option_id IS NOT NULL AND {fo_alias}.option_id IS NOT NULL
             THEN 'feature_setting'
        ELSE 'feature_preview'
    END"""
