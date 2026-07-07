"""One-time migration: recompute canonical_key for all seen_jobs rows after
the normalization change in types.make_canonical_key (2026-07-05).

Usage: uv run python job_scraper/scripts/rekey_seen_jobs.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from job_scraper.src.state import DB_PATH
from job_scraper.src.types import make_canonical_key


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT canonical_key, title, company, location, first_seen FROM seen_jobs"
        " ORDER BY first_seen ASC"
    ).fetchall()
    rekeyed = collided = 0
    for row in rows:
        new_key = make_canonical_key(
            row["title"] or "", row["company"] or "", row["location"] or ""
        )
        if new_key == row["canonical_key"]:
            continue
        try:
            con.execute(
                "UPDATE seen_jobs SET canonical_key = ? WHERE canonical_key = ?",
                (new_key, row["canonical_key"]),
            )
            rekeyed += 1
        except sqlite3.IntegrityError:
            # New key already exists -> this row is a duplicate of an older one.
            con.execute(
                "DELETE FROM seen_jobs WHERE canonical_key = ?",
                (row["canonical_key"],),
            )
            collided += 1
    con.commit()
    print(f"rekeyed={rekeyed} merged_duplicates={collided} total={len(rows)}")


if __name__ == "__main__":
    main()
