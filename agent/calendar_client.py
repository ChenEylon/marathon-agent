import os
import datetime
import pytz
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from agent import config

SCOPES           = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_credentials.json")
TOKEN_FILE       = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "google_token.json")

ACADEMIC_KEYWORDS = [
    # English
    "assignment", "deadline", "submission", "submit", "due", "exam",
    "homework", "hw", "test", "quiz", "midterm", "final", "project", "paper",
    # Hebrew
    "הגשה", "מטלה", "בחינה", "מבחן", "פרויקט", "תרגיל", "עבודה",
]


def get_service():
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("Google Calendar not authorized. Run: python scripts/google_auth.py")

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _event_date(event: dict) -> datetime.date | None:
    start = event.get("start", {})
    date_str = start.get("date") or start.get("dateTime", "")[:10]
    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        return None


def _is_academic(event: dict) -> bool:
    title = (event.get("summary") or "").lower()
    desc  = (event.get("description") or "").lower()
    return any(kw in title or kw in desc for kw in ACADEMIC_KEYWORDS)


def get_upcoming_academic_events(days_ahead: int = 8) -> list[dict]:
    cfg      = config.load()
    tz       = pytz.timezone(cfg["user"]["timezone"])
    today    = datetime.datetime.now(tz).date()
    end_date = today + datetime.timedelta(days=days_ahead)

    time_min = datetime.datetime.combine(today, datetime.time.min).replace(tzinfo=tz).isoformat()
    time_max = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=tz).isoformat()

    service = get_service()
    result  = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    return [e for e in events if _is_academic(e)]


def days_until(event: dict, today: datetime.date) -> int | None:
    event_date = _event_date(event)
    if event_date is None:
        return None
    return (event_date - today).days
