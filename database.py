"""
database.py
Production-grade SQLite data access layer for the Personal Weight Loss Dashboard.

Responsibilities:
- Create and migrate the SQLite schema automatically on first run.
- Provide a single, thread-safe connection helper for Streamlit's script reruns.
- Expose clean CRUD functions used by app.py, analytics.py and utils.py.

No business logic (goal math, predictions, scoring) lives here — that belongs
in analytics.py / utils.py. This file is purely persistence.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "weight_tracker.db"


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------

@contextmanager
def get_connection():
    """
    Context-managed SQLite connection.
    check_same_thread=False is required because Streamlit can execute
    callbacks on different threads across reruns/widgets.
    """
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema creation / migration
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all required tables if they do not already exist."""
    with get_connection() as conn:
        cur = conn.cursor()

        # Main daily logs table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date        TEXT NOT NULL UNIQUE,
                weight_kg       REAL,
                steps           INTEGER,
                calories        REAL,
                protein_g       REAL,
                water_ml        REAL,
                walking_minutes REAL,
                notes           TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            """
        )

        # User profile table (single row, editable from UI)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                name            TEXT,
                gender          TEXT,
                dob             TEXT,
                height_cm       REAL,
                start_weight_kg REAL,
                goal_weight_kg  REAL,
                target_date     TEXT,
                updated_at      TEXT NOT NULL
            )
            """
        )

        # Index for fast date range queries
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_daily_logs_date ON daily_logs(log_date)"
        )

        conn.commit()

        # Seed default profile (Female user as specified) if empty
        cur.execute("SELECT COUNT(*) AS c FROM user_profile")
        count = cur.fetchone()["c"]
        if count == 0:
            now = datetime.now().isoformat()
            cur.execute(
                """
                INSERT INTO user_profile
                    (id, name, gender, dob, height_cm, start_weight_kg,
                     goal_weight_kg, target_date, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "My Profile",
                    "Female",
                    "1998-11-30",
                    152.0,
                    64.0,
                    50.0,
                    "2026-11-30",
                    now,
                ),
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Daily logs CRUD
# ---------------------------------------------------------------------------

def upsert_daily_log(
    log_date: date,
    weight_kg: Optional[float] = None,
    steps: Optional[int] = None,
    calories: Optional[float] = None,
    protein_g: Optional[float] = None,
    water_ml: Optional[float] = None,
    walking_minutes: Optional[float] = None,
    notes: Optional[str] = None,
) -> None:
    """
    Insert a new daily log or update the existing one for that date.
    Only non-None fields overwrite existing values, EXCEPT notes which
    always overwrites (so clearing notes works as expected).
    """
    log_date_str = log_date.isoformat() if isinstance(log_date, date) else str(log_date)
    now = datetime.now().isoformat()

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM daily_logs WHERE log_date = ?", (log_date_str,))
        existing = cur.fetchone()

        if existing is None:
            cur.execute(
                """
                INSERT INTO daily_logs
                    (log_date, weight_kg, steps, calories, protein_g,
                     water_ml, walking_minutes, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_date_str,
                    weight_kg,
                    steps,
                    calories,
                    protein_g,
                    water_ml,
                    walking_minutes,
                    notes,
                    now,
                    now,
                ),
            )
        else:
            merged = {
                "weight_kg": weight_kg if weight_kg is not None else existing["weight_kg"],
                "steps": steps if steps is not None else existing["steps"],
                "calories": calories if calories is not None else existing["calories"],
                "protein_g": protein_g if protein_g is not None else existing["protein_g"],
                "water_ml": water_ml if water_ml is not None else existing["water_ml"],
                "walking_minutes": walking_minutes
                if walking_minutes is not None
                else existing["walking_minutes"],
                "notes": notes if notes is not None else existing["notes"],
            }
            cur.execute(
                """
                UPDATE daily_logs
                SET weight_kg = ?, steps = ?, calories = ?, protein_g = ?,
                    water_ml = ?, walking_minutes = ?, notes = ?, updated_at = ?
                WHERE log_date = ?
                """,
                (
                    merged["weight_kg"],
                    merged["steps"],
                    merged["calories"],
                    merged["protein_g"],
                    merged["water_ml"],
                    merged["walking_minutes"],
                    merged["notes"],
                    now,
                    log_date_str,
                ),
            )
        conn.commit()


def delete_daily_log(log_date: date) -> None:
    log_date_str = log_date.isoformat() if isinstance(log_date, date) else str(log_date)
    with get_connection() as conn:
        conn.execute("DELETE FROM daily_logs WHERE log_date = ?", (log_date_str,))
        conn.commit()


def get_log_for_date(log_date: date) -> Optional[sqlite3.Row]:
    log_date_str = log_date.isoformat() if isinstance(log_date, date) else str(log_date)
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM daily_logs WHERE log_date = ?", (log_date_str,))
        return cur.fetchone()


def get_all_logs_df() -> pd.DataFrame:
    """Return the full daily_logs table as a clean, date-sorted DataFrame."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM daily_logs ORDER BY log_date ASC", conn
        )
    if df.empty:
        return pd.DataFrame(
            columns=[
                "id", "log_date", "weight_kg", "steps", "calories", "protein_g",
                "water_ml", "walking_minutes", "notes", "created_at", "updated_at",
            ]
        )
    df["log_date"] = pd.to_datetime(df["log_date"])
    return df


def get_logs_between(start: date, end: date) -> pd.DataFrame:
    df = get_all_logs_df()
    if df.empty:
        return df
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    mask = (df["log_date"] >= start_ts) & (df["log_date"] <= end_ts)
    return df.loc[mask].copy()


# ---------------------------------------------------------------------------
# User profile CRUD
# ---------------------------------------------------------------------------

def get_profile() -> dict:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM user_profile WHERE id = 1")
        row = cur.fetchone()
        if row is None:
            return {}
        return dict(row)


def update_profile(
    name: str,
    gender: str,
    dob: date,
    height_cm: float,
    start_weight_kg: float,
    goal_weight_kg: float,
    target_date: date,
) -> None:
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE user_profile
            SET name = ?, gender = ?, dob = ?, height_cm = ?,
                start_weight_kg = ?, goal_weight_kg = ?, target_date = ?,
                updated_at = ?
            WHERE id = 1
            """,
            (
                name,
                gender,
                dob.isoformat() if isinstance(dob, date) else str(dob),
                height_cm,
                start_weight_kg,
                goal_weight_kg,
                target_date.isoformat() if isinstance(target_date, date) else str(target_date),
                now,
            ),
        )
        conn.commit()


def get_db_path() -> str:
    return str(DB_PATH)
