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
