import time
import requests
import os
from agent.db import get_connection

STRAVA_API = "https://www.strava.com/api/v3"
RUN_TYPES = {"Run", "VirtualRun", "TrailRun"}


def _get_tokens() -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM strava_tokens WHERE id = 1").fetchone()
        return dict(row) if row else None


def _save_tokens(access_token: str, refresh_token: str, expires_at: int):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO strava_tokens (id, access_token, refresh_token, expires_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                access_token  = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at    = excluded.expires_at
        """, (access_token, refresh_token, expires_at))
        conn.commit()


def get_access_token() -> str:
    tokens = _get_tokens()
    if not tokens:
        raise RuntimeError("No Strava tokens. Run: python scripts/strava_auth.py")

    if time.time() > tokens["expires_at"] - 60:
        resp = requests.post("https://www.strava.com/oauth/token", data={
            "client_id":     os.getenv("STRAVA_CLIENT_ID"),
            "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
            "refresh_token": tokens["refresh_token"],
            "grant_type":    "refresh_token",
        })
        resp.raise_for_status()
        data = resp.json()
        _save_tokens(data["access_token"], data["refresh_token"], data["expires_at"])
        return data["access_token"]

    return tokens["access_token"]


def get_activity(activity_id: int) -> dict:
    token = get_access_token()
    resp = requests.get(
        f"{STRAVA_API}/activities/{activity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json()


def get_recent_activities(limit: int = 5) -> list:
    token = get_access_token()
    resp = requests.get(
        f"{STRAVA_API}/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": limit},
    )
    resp.raise_for_status()
    return resp.json()


def save_activity(activity: dict):
    """Persist a run to the local DB for load/adaptation tracking."""
    if activity.get("type") not in RUN_TYPES:
        return
    speed = activity.get("average_speed", 0)
    pace_sec = round(1000 / speed) if speed > 0 else None
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO activities
                (strava_id, date, distance_km, pace_sec_km, avg_hr, effort)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            activity["id"],
            activity.get("start_date_local", "")[:10],
            round(activity.get("distance", 0) / 1000, 2),
            pace_sec,
            activity.get("average_heartrate"),
            activity.get("suffer_score"),
        ))
        conn.commit()
