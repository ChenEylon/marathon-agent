import datetime
import random
from agent import config, whatsapp_client, garmin

MOTIVATIONAL_QUOTES = [
    "The miracle isn't that I finished. It's that I had the courage to start. – John Bingham",
    "Run when you can, walk if you have to, crawl if you must; just never give up. – Dean Karnazes",
    "Every mile is two in winter. – George Herbert",
    "Your body will argue that there is no justifiable reason to continue. Your only recourse is to call on your spirit. – Tim Noakes",
    "Pain is temporary. Quitting lasts forever. – Lance Armstrong",
    "The long run is what puts the tiger in the cat. – Bill Squires",
    "If you run, you are a runner. It doesn't matter how fast or how far. – John Bingham",
    "The voice inside your head that says you can't do this is a liar. – Unknown",
]


def _day_type(weekday: str) -> str:
    cfg = config.load()
    run_days = [d.lower() for d in cfg["training"]["run_days"]]
    gym_days = [d.lower() for d in cfg["gym_days"]]
    if weekday in run_days:
        return "run"
    elif weekday in gym_days:
        return "gym_only"
    return "rest"


def _hrv_summary_line(hrv: dict | None, body_battery: int | None) -> str:
    parts = []
    if hrv:
        status = hrv.get("status", "").capitalize()
        value  = hrv.get("lastNight")
        parts.append(f"HRV: {value}ms ({status})" if value else f"HRV: {status}")
    if body_battery is not None:
        parts.append(f"Body Battery: {body_battery}%")
    return "📊 Recovery — " + " · ".join(parts) if parts else ""


def build_morning_message(today: datetime.date) -> str:
    cfg     = config.load()
    name    = cfg["user"]["name"]
    weekday = today.strftime("%A").lower()
    dtype   = _day_type(weekday)

    # Always pull recovery data
    hrv          = garmin.get_hrv(today)
    body_battery = garmin.get_body_battery(today)
    garmin.save_daily_reading(today, hrv, body_battery)
    intensity, reason = garmin.get_recovery_advice(hrv, body_battery)
    recovery_line = _hrv_summary_line(hrv, body_battery)

    if dtype == "run":
        # Placeholder workout — Phase 5 will replace with real training plan
        base_workout = "Easy run — 6km at comfortable pace (5:50–6:10/km)"

        if intensity == "rest":
            workout_line = f"⚠️ *Rest recommended today.*\n_{reason}_"
        elif intensity == "easy":
            workout_line = (
                f"📋 Workout (modified): Easy run — 5km, keep pace very relaxed (6:10–6:30/km)\n"
                f"_{reason}_"
            )
        else:
            workout_line = f"📋 Workout: {base_workout}"

        back_note = "\n_Listen to your back and foot. Cut short if anything hurts._"

        return (
            f"Good morning {name}! 🏃\n\n"
            + (f"{recovery_line}\n\n" if recovery_line else "")
            + workout_line
            + back_note
        )

    else:
        quote = random.choice(MOTIVATIONAL_QUOTES)
        label = "Rest day from running — gym focus today." if dtype == "gym_only" else "Full rest day. Recovery is training."

        return (
            f"Good morning {name}! {'💪' if dtype == 'gym_only' else '😴'}\n\n"
            + (f"{recovery_line}\n\n" if recovery_line else "")
            + f"{label}\n\n"
            + f"_{quote}_"
        )


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
