import os
import datetime
import garminconnect
from agent.db import get_connection
from dotenv import load_dotenv

load_dotenv()

TOKENSTORE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "garth_tokens")


def get_client() -> garminconnect.Garmin:
    if not os.path.exists(TOKENSTORE):
        raise RuntimeError("Garmin not authenticated. Run: python scripts/garmin_auth.py")
    email    = os.getenv("GARMIN_EMAIL", "")
    password = os.getenv("GARMIN_PASSWORD", "")
    api = garminconnect.Garmin(email, password)
    api.login(tokenstore=TOKENSTORE)
    return api


def get_hrv(date: datetime.date | None = None) -> dict | None:
    if date is None:
        date = datetime.date.today()
    try:
        api = get_client()
        data = api.get_hrv_data(date.isoformat())
        return data.get("hrvSummary") if data else None
    except Exception as e:
        print(f"⚠️  Garmin HRV fetch failed: {e}")
        return None


def get_body_battery(date: datetime.date | None = None) -> int | None:
    if date is None:
        date = datetime.date.today()
    try:
        api = get_client()
        data = api.get_body_battery(date.isoformat(), date.isoformat())
        if not data:
            return None
        readings = data[0].get("bodyBatteryValuesArray", [])
        if readings:
            return readings[-1][1]
        return None
    except Exception as e:
        print(f"⚠️  Garmin Body Battery fetch failed: {e}")
        return None


def save_daily_reading(date: datetime.date, hrv: dict | None, body_battery: int | None):
    hrv_status     = hrv.get("status") if hrv else None
    hrv_last_night = hrv.get("lastNight") if hrv else None
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO garmin_readings (date, hrv_status, hrv_last_night, body_battery)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                hrv_status     = excluded.hrv_status,
                hrv_last_night = excluded.hrv_last_night,
                body_battery   = excluded.body_battery
        """, (date.isoformat(), hrv_status, hrv_last_night, body_battery))
        conn.commit()


def get_recovery_advice(hrv: dict | None, body_battery: int | None) -> tuple[str, str | None]:
    """Returns (intensity_level, reason_or_None). intensity_level: 'full' | 'easy' | 'rest'"""
    status = (hrv.get("status") or "").upper() if hrv else None
    bb     = body_battery or 0

    if status == "POOR" or bb < 25:
        return "rest", "Your recovery is very low today (HRV poor / Body Battery critical)"
    if status in ("LOW", "UNBALANCED") or bb < 45:
        return "easy", "Recovery is below baseline — keep it easy today"
    return "full", None
