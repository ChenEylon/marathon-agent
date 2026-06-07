import json
import os
import datetime
import anthropic
from agent import config, training_plan
from agent.db import get_connection

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


_SYSTEM = """You are a personal AI running coach for {name}, training for a marathon on {marathon_date}.

Key facts:
- Medical history: stress fracture in foot + herniated disc — always err on the side of caution
- Also trains in the gym 4-5 days/week, which adds to total load
- Currently in training week {current_week} of 34
- Pace zones: Easy {easy_pace} /km · Tempo {tempo_pace} /km · Marathon goal {marathon_pace} /km

This week's plan:
{week_plan}

Coaching style: concise, friendly, actionable. No fluff. If the athlete writes in Hebrew, reply in Hebrew."""


def _build_system() -> str:
    cfg          = config.load()
    today        = datetime.date.today()
    current_week = training_plan.get_current_week(today)
    week_summary = training_plan.get_week_summary(current_week)

    week_plan = "\n".join(
        f"  {w['day_of_week'].capitalize()}: {w['workout_type']} {w['distance_km']}km @ {w['pace_target']}/km"
        for w in week_summary
    ) or "  No workouts loaded for this week yet."

    return _SYSTEM.format(
        name=cfg["user"]["name"],
        marathon_date=cfg["training"]["marathon_date"],
        current_week=current_week,
        easy_pace=cfg["training"]["easy_pace_range"],
        tempo_pace=cfg["training"]["tempo_pace_range"],
        marathon_pace=cfg["training"]["marathon_pace_range"],
        week_plan=week_plan,
    )


def get_history(limit: int = 40) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM chat_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def chat(user_message: str) -> str:
    history = get_history(limit=20)
    messages = [{"role": r["role"], "content": r["content"]} for r in history]
    messages.append({"role": "user", "content": user_message})

    _save("user", user_message)

    try:
        resp = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=_build_system(),
            messages=messages,
        )
        reply = resp.content[0].text
    except Exception as e:
        err = str(e).lower()
        if "credit" in err or "balance" in err or "billing" in err:
            reply = "The coach is currently unavailable — account credits need topping up. Check back soon."
        elif "rate" in err or "429" in err:
            reply = "Too many messages at once — give it a moment and try again."
        elif "timeout" in err or "connection" in err:
            reply = "Connection timed out. Check your internet and try again."
        else:
            reply = "Couldn't reach the coach right now. Try again in a moment."

    _save("assistant", reply)
    return reply


def _save(role: str, content: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_history (role, content) VALUES (?, ?)",
            (role, content),
        )
        conn.commit()
