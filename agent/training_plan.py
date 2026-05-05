import datetime
from agent import config
from agent.db import get_connection


def get_current_week(today: datetime.date | None = None) -> int:
    if today is None:
        today = datetime.date.today()
    cfg        = config.load()
    start_date = datetime.date.fromisoformat(cfg["training"]["plan_start_date"])
    delta      = (today - start_date).days
    return max(1, min(34, delta // 7 + 1))


def get_todays_workout(today: datetime.date | None = None) -> dict | None:
    if today is None:
        today = datetime.date.today()
    weekday     = today.strftime("%A").lower()
    week_number = get_current_week(today)

    with get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM training_plan
            WHERE week_number = ? AND day_of_week = ?
        """, (week_number, weekday)).fetchone()
    return dict(row) if row else None


def get_week_summary(week_number: int | None = None) -> list[dict]:
    if week_number is None:
        week_number = get_current_week()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM training_plan
            WHERE week_number = ?
            ORDER BY CASE day_of_week
                WHEN 'monday' THEN 1
                WHEN 'wednesday' THEN 2
                WHEN 'saturday' THEN 3
            END
        """, (week_number,)).fetchall()
    return [dict(r) for r in rows]


def get_recent_activities(days: int = 14) -> list[dict]:
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM activities
            WHERE date >= ?
            ORDER BY date DESC
        """, (since,)).fetchall()
    return [dict(r) for r in rows]


def save_feedback(date: datetime.date, feeling: int, notes: str = ""):
    week = get_current_week(date)
    day  = date.strftime("%A").lower()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO workout_feedback (date, week_number, day_of_week, feeling, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET feeling = excluded.feeling, notes = excluded.notes
        """, (date.isoformat(), week, day, feeling, notes))
        conn.commit()
