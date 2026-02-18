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
# Status is derived from production_date/beta_date at query time.
# Explicit override statuses (delayed, deprecated) are preserved as-is.

def _computed_status(date_prefix: str, status_col: str, released_label: str = "released") -> str:
    """Build a CASE expression that computes status from dates.

    Explicit lifecycle statuses (delayed, deprecated, preview, optional, default_on,
    default_optional) are preserved as-is. Date-based computation only applies when
    the stored status is 'pending' (the default).

    Args:
        date_prefix: Table alias for production_date/beta_date columns (e.g. "fo", "fs").
        status_col: Fully-qualified status column (e.g. "fo.status").
        released_label: Label for the 'released' state ('released' for options, 'active' for settings).
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


# Feature options: fo.status → computed from fo.production_date / fo.beta_date
OPTION_STATUS_SQL = _computed_status("fo", "fo.status", "released")

# Feature settings: fs.status → computed from fs.production_date / fs.beta_date
SETTING_STATUS_SQL = _computed_status("fs", "fs.status", "active")


def announcement_status_sql(fa_alias: str = "fa", fo_alias: str = "fo") -> str:
    """Compute status for announcements that join to feature_options.

    Uses COALESCE so announcement-level dates take precedence over option-level.
    Preserves explicit lifecycle statuses from the linked feature option.
    """
    return f"""CASE
        WHEN {fo_alias}.status IN ('delayed', 'deprecated', 'preview', 'optional', 'default_on', 'default_optional')
             THEN {fo_alias}.status
        WHEN COALESCE({fa_alias}.production_date, {fo_alias}.production_date) IS NOT NULL
             AND COALESCE({fa_alias}.production_date, {fo_alias}.production_date) <= date('now') THEN 'released'
        WHEN COALESCE({fa_alias}.beta_date, {fo_alias}.beta_date) IS NOT NULL
             AND COALESCE({fa_alias}.beta_date, {fo_alias}.beta_date) <= date('now') THEN 'beta'
        WHEN {fa_alias}.option_id IS NOT NULL THEN 'pending'
        ELSE NULL
    END"""
