import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strava_tokens (
                id      INTEGER PRIMARY KEY CHECK (id = 1),
                access_token   TEXT NOT NULL,
                refresh_token  TEXT NOT NULL,
                expires_at     INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                strava_id   INTEGER PRIMARY KEY,
                date        TEXT NOT NULL,
                distance_km REAL,
                pace_sec_km REAL,
                avg_hr      REAL,
                effort      REAL,
                processed   INTEGER DEFAULT 0
            )
        """)
        conn.commit()
