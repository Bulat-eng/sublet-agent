"""
SQLite-backed dedup store. Adapted from rental-agent/db.py.
Tracks which listing IDs we've already notified about so we don't spam.
State is committed back to the repo by the GitHub Actions workflow.
"""

from __future__ import annotations

import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)
DB_PATH = os.environ.get("DB_PATH", "state.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            id      TEXT PRIMARY KEY,
            url     TEXT,
            source  TEXT,
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS source_runs (
            source   TEXT PRIMARY KEY,
            last_run TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"Database initialised at {DB_PATH}")


def is_seen(listing_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM seen WHERE id = ?", (listing_id,))
    found = c.fetchone() is not None
    conn.close()
    return found


def mark_seen(listing_id: str, url: str, source: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO seen (id, url, source) VALUES (?, ?, ?)",
        (listing_id, url, source),
    )
    conn.commit()
    conn.close()


def get_last_run(source: str) -> datetime | None:
    """Return the UTC datetime a source last ran, or None if it never has."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT last_run FROM source_runs WHERE source = ?", (source,))
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        return None
    try:
        return datetime.fromisoformat(row[0])
    except ValueError:
        return None


def set_last_run(source: str):
    """Record that a source just ran (naive UTC ISO timestamp)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO source_runs (source, last_run) VALUES (?, ?)",
        (source, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def purge_old(days: int = 45):
    """Remove entries older than `days` so the DB stays lean."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM seen WHERE seen_at < datetime('now', ?)", (f"-{days} days",))
    deleted = conn.total_changes
    conn.commit()
    conn.close()
    if deleted:
        logger.info(f"Purged {deleted} old entries from DB")


def count() -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM seen")
    n = c.fetchone()[0]
    conn.close()
    return n
