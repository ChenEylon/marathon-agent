import datetime
import pytz
from agent import config, whatsapp_client, calendar_client
from agent.db import get_connection


def _reminder_already_sent(event_id: str, days_before: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM sent_reminders WHERE event_id = ? AND days_before = ?",
            (event_id, days_before),
        ).fetchone()
        return row is not None


def _mark_sent(event_id: str, days_before: int):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sent_reminders (event_id, days_before) VALUES (?, ?)",
            (event_id, days_before),
        )
        conn.commit()


def _format_event_date(event: dict) -> str:
    start    = event.get("start", {})
    date_str = start.get("date") or start.get("dateTime", "")[:10]
    try:
        d = datetime.date.fromisoformat(date_str)
        return d.strftime("%A, %B %d")
    except ValueError:
        return date_str


def check_and_send_deadline_reminders():
    cfg   = config.load()
    phone = cfg["user"]["phone"]
    name  = cfg["user"]["name"]
    tz    = pytz.timezone(cfg["user"]["timezone"])
    today = datetime.datetime.now(tz).date()

    try:
        events = calendar_client.get_upcoming_academic_events(days_ahead=8)
    except Exception as e:
        print(f"⚠️  Calendar check failed: {e}")
        return

    for event in events:
        days_left = calendar_client.days_until(event, today)
        if days_left is None:
            continue

        event_id = event.get("id", "")
        title    = event.get("summary", "Untitled event")
        date_str = _format_event_date(event)

        for threshold in cfg["reminders"]["deadline_days_before"]:
            if days_left == threshold and not _reminder_already_sent(event_id, threshold):
                if threshold == 1:
                    urgency = "⚠️ *Tomorrow!*"
                    note    = "Make sure you're ready, Chen."
                else:
                    urgency = f"📅 *{threshold} days away*"
                    note    = f"You have {threshold} days — plan ahead."

                message = (
                    f"📚 Deadline reminder — {urgency}\n\n"
                    f"*{title}*\n"
                    f"Due: {date_str}\n\n"
                    f"{note}"
                )

                if whatsapp_client.send_message(phone, message):
                    _mark_sent(event_id, threshold)
                    print(f"✅ Deadline reminder sent: '{title}' ({threshold}d)")
