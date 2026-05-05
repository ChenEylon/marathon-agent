import os
import json
import datetime
import anthropic
from agent import config, training_plan

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _recent_summary(activities: list[dict]) -> str:
    if not activities:
        return "No recent runs logged."
    lines = []
    for a in activities[:5]:
        pace_str = ""
        if a.get("pace_sec_km"):
            m, s = divmod(int(a["pace_sec_km"]), 60)
            pace_str = f" @ {m}:{s:02d}/km"
        hr_str    = f", HR {int(a['avg_hr'])}bpm" if a.get("avg_hr") else ""
        effort_str = f", effort {int(a['effort'])}" if a.get("effort") else ""
        lines.append(f"  • {a['date']}: {a['distance_km']}km{pace_str}{hr_str}{effort_str}")
    return "\n".join(lines)


def adapt_workout(
    planned: dict,
    hrv: dict | None,
    body_battery: int | None,
    today: datetime.date | None = None,
) -> dict:
    """
    Calls Claude to analyse recovery + recent training and return an adapted workout.
    Returns dict with keys: decision, distance_km, pace_target, description, coach_note.
    Falls back to the original plan if the API call fails.
    """
    if today is None:
        today = datetime.date.today()

    cfg          = config.load()
    week_number  = training_plan.get_current_week(today)
    recent       = training_plan.get_recent_activities(days=14)
    week_summary = training_plan.get_week_summary(week_number)

    hrv_text = "Not available"
    if hrv:
        status = hrv.get("status", "unknown")
        value  = hrv.get("lastNight")
        hrv_text = f"{status} ({value}ms)" if value else status

    week_plan_text = "\n".join(
        f"  {w['day_of_week'].capitalize()}: {w['workout_type']} {w['distance_km']}km"
        for w in week_summary
    )

    system_prompt = """You are a smart running coach AI for Chen, a marathon runner.
Chen has a history of a stress fracture in the foot and a herniated disc — always err on the side of caution.
Chen also trains in the gym 4-5 days a week, which adds to overall training load.
Your job: analyse the daily recovery data and recent training, then decide whether to run the workout as planned, modify it, or recommend rest.
Always respond with valid JSON only — no markdown, no explanation outside the JSON."""

    user_prompt = f"""Today: {today.strftime('%A, %B %d')} — Week {week_number} of 34

PLANNED WORKOUT:
  Type: {planned['workout_type']}
  Distance: {planned['distance_km']}km
  Pace: {planned['pace_target']}/km
  Description: {planned['description']}

THIS WEEK'S PLAN:
{week_plan_text}

RECOVERY DATA:
  Morning HRV: {hrv_text}
  Body Battery: {body_battery if body_battery is not None else 'Not available'}%

RECENT RUNS (last 14 days):
{_recent_summary(recent)}

Respond ONLY with this JSON (no other text):
{{
  "decision": "as_planned" | "modified" | "rest",
  "distance_km": <number>,
  "pace_target": "<pace range string>",
  "description": "<concise workout description>",
  "coach_note": "<1-2 sentence explanation for Chen — friendly tone>"
}}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        result = json.loads(response.content[0].text)
        return result
    except Exception as e:
        print(f"⚠️  Adaptation engine failed: {e} — using original plan")
        return {
            "decision":    "as_planned",
            "distance_km": planned["distance_km"],
            "pace_target": planned["pace_target"],
            "description": planned["description"],
            "coach_note":  None,
        }
