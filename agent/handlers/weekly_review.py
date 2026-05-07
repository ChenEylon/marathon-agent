import datetime
import json
import anthropic
import os
from agent import config, whatsapp_client, strava, training_plan
from agent.db import get_connection


def _get_last_week_feedback() -> list[dict]:
    since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM workout_feedback WHERE date >= ? ORDER BY date",
            (since,)
        ).fetchall()
    return [dict(r) for r in rows]


def _get_last_week_activities() -> list[dict]:
    return strava.get_recent_activities(limit=10)


def _get_last_week_planned(today: datetime.date) -> list[dict]:
    week = training_plan.get_current_week(today)
    # also grab previous week since we're reviewing it
    prev_week = max(1, week - 1)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM training_plan WHERE week_number = ? ORDER BY id",
            (prev_week,)
        ).fetchall()
    return [dict(r) for r in rows]


def _update_config_paces(easy: str, tempo: str, marathon: str):
    import re
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml")
    with open(cfg_path, "r") as f:
        content = f.read()
    content = re.sub(r'easy_pace_range:.*', f'easy_pace_range: "{easy}"', content)
    content = re.sub(r'tempo_pace_range:.*', f'tempo_pace_range: "{tempo}"', content)
    content = re.sub(r'marathon_pace_range:.*', f'marathon_pace_range: "{marathon}"', content)
    with open(cfg_path, "w") as f:
        f.write(content)


def _update_future_plan_paces(current_week: int, easy: str, tempo: str, marathon: str):
    pace_map = {"easy": easy, "long": easy, "tempo": tempo, "intervals": tempo, "race": marathon}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, workout_type FROM training_plan WHERE week_number > ?",
            (current_week,)
        ).fetchall()
        for row in rows:
            new_pace = pace_map.get(row["workout_type"])
            if new_pace:
                conn.execute(
                    "UPDATE training_plan SET pace_target = ? WHERE id = ?",
                    (new_pace, row["id"])
                )
        conn.commit()


def run_weekly_review():
    today = datetime.date.today()
    cfg   = config.load()
    phone = cfg["user"]["phone"]
    name  = cfg["user"]["name"]

    activities = _get_last_week_activities()
    feedback   = _get_last_week_feedback()
    planned    = _get_last_week_planned(today)
    current_week = training_plan.get_current_week(today)

    if not activities:
        print("⏭️  Weekly review: no activities last week, skipping")
        return

    # Build context for Claude
    act_summary = [
        {
            "date": a.get("date", ""),
            "distance_km": round(a.get("distance", 0) / 1000, 1),
            "avg_pace_per_km": _seconds_to_pace(a.get("moving_time", 0), a.get("distance", 1)),
            "type": a.get("sport_type", "Run"),
        }
        for a in activities
    ]
    fb_summary = [{"date": f["date"], "feeling": f["feeling"]} for f in feedback]
    plan_summary = [
        {"day": p["day_of_week"], "type": p["workout_type"],
         "distance_km": p["distance_km"], "target_pace": p["pace_target"]}
        for p in planned
    ]

    prompt = f"""You are a running coach reviewing {name}'s training week {current_week - 1}.

Current pace zones:
- Easy: {cfg['training']['easy_pace_range']} /km
- Tempo: {cfg['training']['tempo_pace_range']} /km
- Marathon goal: {cfg['training']['marathon_pace_range']} /km

Planned workouts last week:
{json.dumps(plan_summary, indent=2)}

Actual activities (from Strava):
{json.dumps(act_summary, indent=2)}

Post-run feeling scores (1=very hard, 5=very easy):
{json.dumps(fb_summary, indent=2)}

Based on the actual performance vs planned, recalibrate the pace zones for the coming weeks.
Rules:
- If easy runs were consistently faster than target AND feeling was 4-5, tighten the easy range
- If runs felt very hard (1-2) or athlete ran slower, loosen the range
- Keep changes gradual (max 10-15 sec/km shift per week)
- Marathon is {cfg['training']['marathon_date']}, currently week {current_week} of 34

Respond in JSON only:
{{
  "easy_pace_range": "M:SS-M:SS",
  "tempo_pace_range": "M:SS-M:SS",
  "marathon_pace_range": "M:SS-M:SS",
  "summary": "2-sentence summary in Hebrew for the athlete",
  "changed": true/false
}}"""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        data = json.loads(resp.content[0].text)
    except Exception as e:
        print(f"❌ Weekly review Claude error: {e}")
        return

    if data.get("changed"):
        _update_config_paces(
            data["easy_pace_range"],
            data["tempo_pace_range"],
            data["marathon_pace_range"]
        )
        _update_future_plan_paces(
            current_week,
            data["easy_pace_range"],
            data["tempo_pace_range"],
            data["marathon_pace_range"]
        )
        print(f"✅ Paces recalibrated: easy={data['easy_pace_range']} tempo={data['tempo_pace_range']}")

    msg = (
        f"📊 *סיכום שבוע {current_week - 1}*\n\n"
        f"{data['summary']}\n\n"
    )
    if data.get("changed"):
        msg += (
            f"🔧 *עדכון קצבים:*\n"
            f"  קל: {data['easy_pace_range']} /ק\"מ\n"
            f"  טמפו: {data['tempo_pace_range']} /ק\"מ\n"
            f"  מרתון: {data['marathon_pace_range']} /ק\"מ"
        )
    else:
        msg += "✅ הקצבים נשארים כמו שהם — הכל נראה בסדר."

    whatsapp_client.send_message(phone, msg)
    print(f"✅ Weekly review sent for week {current_week - 1}")


def _seconds_to_pace(moving_time: int, distance_m: float) -> str:
    if distance_m < 100:
        return "N/A"
    pace_sec = moving_time / (distance_m / 1000)
    mins = int(pace_sec // 60)
    secs = int(pace_sec % 60)
    return f"{mins}:{secs:02d}"
