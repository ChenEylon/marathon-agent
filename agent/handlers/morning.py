import datetime
import random
from agent import config, whatsapp_client, garmin, training_plan, adaptation

MOTIVATIONAL_QUOTES = [
    "The miracle isn't that I finished. It's that I had the courage to start. – John Bingham",
    "Run when you can, walk if you have to, crawl if you must; just never give up. – Dean Karnazes",
    "Your body will argue that there is no justifiable reason to continue. Your only recourse is to call on your spirit. – Tim Noakes",
    "Pain is temporary. Quitting lasts forever. – Lance Armstrong",
    "The long run is what puts the tiger in the cat. – Bill Squires",
    "If you run, you are a runner. It doesn't matter how fast or how far. – John Bingham",
    "The voice inside your head that says you can't do this is a liar. – Unknown",
    "Champions aren't made in the gyms. They are made from something deep inside them. – Muhammad Ali",
]


def _recovery_line(hrv: dict | None, body_battery: int | None) -> str:
    parts = []
    if hrv:
        status = hrv.get("status", "").capitalize()
        value  = hrv.get("lastNight")
        parts.append(f"HRV: {value}ms ({status})" if value else f"HRV: {status}")
    if body_battery is not None:
        parts.append(f"Body Battery: {body_battery}%")
    return "📊 " + " · ".join(parts) if parts else ""


def _weeks_to_marathon(today: datetime.date) -> str:
    cfg = config.load()
    marathon_date = datetime.date.fromisoformat(cfg["training"]["marathon_date"])
    weeks = (marathon_date - today).days // 7
    if weeks <= 0:
        return "Race week! 🏁"
    return f"{weeks} weeks to marathon"


def build_morning_message(today: datetime.date) -> str:
    cfg     = config.load()
    name    = cfg["user"]["name"]
    weekday = today.strftime("%A").lower()

    # Pull recovery data
    hrv          = garmin.get_hrv(today)
    body_battery = garmin.get_body_battery(today)
    garmin.save_daily_reading(today, hrv, body_battery)

    recovery_line  = _recovery_line(hrv, body_battery)
    weeks_to_race  = _weeks_to_marathon(today)
    week_number    = training_plan.get_current_week(today)

    run_days = [d.lower() for d in cfg["training"]["run_days"]]
    gym_days = [d.lower() for d in cfg["gym_days"]]

    if weekday in run_days:
        planned = training_plan.get_todays_workout(today)
        if not planned:
            return f"Good morning {name}! No workout found for today — rest up. ({weeks_to_race})"

        adapted = adaptation.adapt_workout(planned, hrv, body_battery, today)

        emoji = {"easy": "🏃", "long": "🏃‍♂️", "tempo": "⚡", "intervals": "🔥", "race": "🏆", "rest": "😴"}.get(adapted["decision"] if adapted["decision"] == "rest" else planned["workout_type"], "🏃")

        lines = [f"Good morning {name}! {emoji}"]
        lines.append(f"_{weeks_to_race} · Week {week_number}_\n")

        if recovery_line:
            lines.append(recovery_line + "\n")

        if adapted["decision"] == "rest":
            lines.append("⚠️ *Rest recommended today*")
        elif adapted["decision"] == "modified":
            lines.append(f"📋 *Workout (adjusted):* {adapted['description']}")
            lines.append(f"📏 {adapted['distance_km']}km · {adapted['pace_target']}/km")
        else:
            lines.append(f"📋 *Workout:* {adapted['description']}")
            lines.append(f"📏 {planned['distance_km']}km · {planned['pace_target']}/km")

        if adapted.get("coach_note"):
            lines.append(f"\n_{adapted['coach_note']}_")

        lines.append("\n_Listen to your back and foot. Cut short if anything hurts._")

        # Feeling prompt for feedback loop
        lines.append("\n_After your run, reply with how it felt: 1 (very hard) → 5 (too easy)_")

        return "\n".join(lines)

    else:
        quote = random.choice(MOTIVATIONAL_QUOTES)
        if weekday in gym_days:
            label = "Gym day — no running today. 💪"
        else:
            label = "Rest day — recovery is training. 😴"

        lines = [f"Good morning {name}!"]
        lines.append(f"_{weeks_to_race} · Week {week_number}_\n")
        if recovery_line:
            lines.append(recovery_line + "\n")
        lines.append(label)
        lines.append(f"\n_{quote}_")
        return "\n".join(lines)


def send_morning_message():
    cfg   = config.load()
    phone = cfg["user"]["phone"]
    if not phone:
        print("⚠️  No phone number configured in config.yaml")
        return

    today   = datetime.date.today()
    message = build_morning_message(today)
    success = whatsapp_client.send_message(phone, message)
    print(f"{'✅' if success else '❌'} Morning message {'sent' if success else 'failed'} for {today}")
