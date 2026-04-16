"""
SQLite-backed state: deduplication store and run log.

Tables
------
seen_jobs   — canonical_key → first_seen date; prevents re-fetching duplicates
run_log     — one row per run with aggregate stats
error_log   — individual errors from any run
"""
import os
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# DB_PATH can be overridden by the DB_PATH env var.
# Default: state.db next to this package (works on Windows).
# In sandboxed/read-only mounts use DB_PATH=/tmp/job_scraper.db
_default_db = Path(__file__).parent.parent / "state.db"
DB_PATH = Path(os.environ.get("DB_PATH", str(_default_db)))


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                canonical_key TEXT PRIMARY KEY,
                title         TEXT,
                company       TEXT,
                location      TEXT,
                source        TEXT,
                apply_url     TEXT,
                date_posted   TEXT,
                first_seen    TEXT NOT NULL,
                fetched_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS run_log (
                run_id            TEXT PRIMARY KEY,
                started_at        TEXT NOT NULL,
                finished_at       TEXT,
                total_fetched     INTEGER DEFAULT 0,
                new_jobs          INTEGER DEFAULT 0,
                skipped           INTEGER DEFAULT 0,
                sources_json      TEXT,
                errors_json       TEXT,
                status            TEXT DEFAULT 'running'
            );

            CREATE TABLE IF NOT EXISTS error_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id     TEXT,
                source     TEXT,
                message    TEXT,
                ts         TEXT NOT NULL
            );
        """)
        # Migrate existing databases that predate fetched_at column.
        existing = {row[1] for row in con.execute("PRAGMA table_info(seen_jobs)")}
        if "fetched_at" not in existing:
            con.execute("ALTER TABLE seen_jobs ADD COLUMN fetched_at TEXT")
        # Drop description column if present from older schema — too bulky for a dedupe store.
        if "description" in existing:
            con.execute("ALTER TABLE seen_jobs DROP COLUMN description")


def prune_old(days: int | None = None) -> int:
    """Delete seen_jobs rows older than `days` days. Returns number of rows deleted."""
    retention = days if days is not None else int(os.environ.get("DEDUP_RETENTION_DAYS", "30"))
    with _conn() as con:
        cur = con.execute("""
            DELETE FROM seen_jobs
            WHERE first_seen < datetime('now', ? || ' days')
        """, (f"-{retention}",))
        pruned = cur.rowcount
    if pruned:
        import logging
        logging.getLogger(__name__).info("state: pruned %d seen_jobs older than %d days", pruned, retention)
    return pruned


def mark_seen_if_new(canonical_key: str, title: str, company: str,
                     location: str, source: str, apply_url: str,
                     date_posted: str, fetched_at: Optional[str] = None) -> bool:
    """Insert the job atomically. Returns True if inserted (new), False if already seen."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        cur = con.execute("""
            INSERT OR IGNORE INTO seen_jobs
              (canonical_key, title, company, location, source, apply_url,
               date_posted, first_seen, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (canonical_key, title, company, location, source,
              apply_url, date_posted, now, fetched_at))
        return cur.rowcount > 0


def start_run(run_id: str, started_at: str) -> None:
    with _conn() as con:
        con.execute("""
            INSERT INTO run_log (run_id, started_at, status)
            VALUES (?, ?, 'running')
        """, (run_id, started_at))


def finish_run(run_id: str, finished_at: str, total_fetched: int,
               new_jobs: int, skipped: int,
               sources: dict, errors: list[str]) -> None:
    with _conn() as con:
        con.execute("""
            UPDATE run_log
            SET finished_at   = ?,
                total_fetched = ?,
                new_jobs      = ?,
                skipped       = ?,
                sources_json  = ?,
                errors_json   = ?,
                status        = 'done'
            WHERE run_id = ?
        """, (finished_at, total_fetched, new_jobs, skipped,
              json.dumps(sources), json.dumps(errors), run_id))


def log_error(run_id: str, source: str, message: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.execute("""
            INSERT INTO error_log (run_id, source, message, ts)
            VALUES (?, ?, ?, ?)
        """, (run_id, source, message, now))


def get_recent_runs(limit: int = 7) -> list[dict]:
    with _conn() as con:
        rows = con.execute("""
            SELECT * FROM run_log
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["sources"] = json.loads(d.pop("sources_json") or "{}")
            d["errors"]  = json.loads(d.pop("errors_json")  or "[]")
            result.append(d)
        return result


def get_jobs(
    since: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """
    Query seen_jobs with optional filters.

    since  — ISO 8601 date string, e.g. '2026-03-01'; filters on first_seen
    source — 'indeed' | 'linkedin' | 'nvb'
    limit  — max rows to return (default 200)
    offset — pagination offset
    """
    clauses: list[str] = []
    params:  list      = []

    if since:
        clauses.append("first_seen >= ?")
        params.append(since)
    if source:
        clauses.append("source = ?")
        params.append(source)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params += [limit, offset]

    with _conn() as con:
        rows = con.execute(f"""
            SELECT canonical_key, title, company, location, source,
                   apply_url, date_posted, first_seen, fetched_at
            FROM seen_jobs
            {where}
            ORDER BY first_seen DESC
            LIMIT ? OFFSET ?
        """, params).fetchall()
        return [dict(r) for r in rows]


def get_recent_errors(limit: int = 20) -> list[dict]:
    with _conn() as con:
        rows = con.execute("""
            SELECT * FROM error_log
            ORDER BY ts DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_seen_count() -> int:
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
