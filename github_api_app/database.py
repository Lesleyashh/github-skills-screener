from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path("data/app.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initialise database schema.

    NOTE:
    - No migrations are performed.
    - If the schema changes, delete data/app.db and rerun.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS developer_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            github_user_id INTEGER NOT NULL UNIQUE,
            github_username TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            raw_user_json TEXT,
            signals_json TEXT
        );

        CREATE TABLE IF NOT EXISTS job_descriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            name TEXT NOT NULL,
            version INTEGER NOT NULL,
            criteria_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(job_id, version)
        );

        CREATE TABLE IF NOT EXISTS match_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            developer_profile_id INTEGER NOT NULL,
            job_description_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            score INTEGER NOT NULL,
            reasons_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            matched_at TEXT NOT NULL,
            UNIQUE(developer_profile_id, job_description_id),
            FOREIGN KEY (developer_profile_id) REFERENCES developer_profiles(id),
            FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id)
        );
        """
    )

    conn.commit()
    conn.close()


# -----------------------------
# Writes
# -----------------------------
def upsert_developer_profile(
    github_user_id: int,
    github_username: str,
    raw_user: Dict[str, Any],
    signals: Dict[str, Any],
) -> int:
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO developer_profiles (
            github_user_id,
            github_username,
            created_at,
            updated_at,
            raw_user_json,
            signals_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(github_user_id) DO UPDATE SET
            github_username = excluded.github_username,
            updated_at = excluded.updated_at,
            raw_user_json = excluded.raw_user_json,
            signals_json = excluded.signals_json
        """,
        (
            int(github_user_id),
            github_username,
            now,
            now,
            json.dumps(raw_user),
            json.dumps(signals),
        ),
    )

    conn.commit()

    cur.execute(
        "SELECT id FROM developer_profiles WHERE github_user_id = ?",
        (int(github_user_id),),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        raise RuntimeError("Failed to upsert developer profile")

    return int(row["id"])


def insert_job_description(
    job_id: str,
    name: str,
    version: int,
    criteria: Dict[str, Any],
) -> int:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO job_descriptions (
            job_id,
            name,
            version,
            criteria_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            job_id,
            name,
            version,
            json.dumps(criteria),
            datetime.utcnow().isoformat(),
        ),
    )

    conn.commit()

    cur.execute(
        "SELECT id FROM job_descriptions WHERE job_id = ? AND version = ?",
        (job_id, version),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        raise RuntimeError("Failed to load job description")

    return int(row["id"])


def insert_match_result(
    developer_profile_id: int,
    job_description_id: int,
    status: str,
    score: int,
    reasons: List[str],
    warnings: List[str],
) -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR REPLACE INTO match_results (
            developer_profile_id,
            job_description_id,
            status,
            score,
            reasons_json,
            warnings_json,
            matched_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            developer_profile_id,
            job_description_id,
            status,
            score,
            json.dumps(reasons),
            json.dumps(warnings),
            datetime.utcnow().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


# -----------------------------
# Reads
# -----------------------------


def fetch_report_for_job(
    job_id: str,
    version: Optional[int] = None,
    min_score: int = 0,
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    # Default to latest version for that job_id
    if version is None:
        cur.execute(
            "SELECT MAX(version) AS v FROM job_descriptions WHERE job_id = ?",
            (str(job_id),),
        )
        row = cur.fetchone()
        if row is None or row["v"] is None:
            conn.close()
            return []
        version = int(row["v"])

    cur.execute(
        """
        SELECT
            jd.name AS job_name,
            jd.version AS job_version,
            jd.job_id AS job_id,

            dp.github_user_id AS github_user_id,
            dp.github_username AS github_username,
            dp.updated_at AS profile_updated_at,

            mr.status AS status,
            mr.score AS score,
            mr.reasons_json AS reasons_json,
            mr.warnings_json AS warnings_json,
            mr.matched_at AS matched_at
        FROM match_results mr
        JOIN developer_profiles dp ON dp.id = mr.developer_profile_id
        JOIN job_descriptions jd ON jd.id = mr.job_description_id
        WHERE jd.job_id = ? AND jd.version = ? AND mr.score >= ?
        ORDER BY mr.score DESC, dp.github_username ASC
        """,
        (str(job_id), int(version), int(min_score)),
    )

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# -----------------------------
# Retention
# -----------------------------
def purge_old_data(days: int = 90) -> Dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM match_results
        WHERE developer_profile_id IN (
            SELECT id FROM developer_profiles
            WHERE (julianday('now') - julianday(updated_at)) > ?
        )
        """,
        (days,),
    )
    deleted_matches = cur.rowcount

    cur.execute(
        """
        DELETE FROM developer_profiles
        WHERE (julianday('now') - julianday(updated_at)) > ?
        """,
        (days,),
    )
    deleted_profiles = cur.rowcount

    conn.commit()
    conn.close()

    return {
        "deleted_match_results": deleted_matches,
        "deleted_developer_profiles": deleted_profiles,
    }
