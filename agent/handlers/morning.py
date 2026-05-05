import datetime
from agent import config, whatsapp_client

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


def get_day_type(weekday: str) -> str:
    cfg = config.load()
    run_days = [d.lower() for d in cfg["training"]["run_days"]]
    gym_days = [d.lower() for d in cfg["gym_days"]]

    if weekday in run_days:
        return "run"
    elif weekday in gym_days:
        return "gym_only"
    else:
        return "rest"


def build_morning_message(today: datetime.date) -> str:
    cfg = config.load()
    name = cfg["user"]["name"]
    weekday = today.strftime("%A").lower()
    day_type = get_day_type(weekday)

    if day_type == "run":
        # Placeholder — will be replaced by real training plan in Phase 5
        return (
            f"Good morning {name}! 🏃\n\n"
            f"Today is a *running day*.\n\n"
            f"📋 Workout: Easy run — 6km at comfortable pace (5:50–6:10/km)\n\n"
            f"Listen to your body. If anything feels off with your back or foot, cut it short."
        )
    elif day_type == "gym_only":
        import random
        quote = random.choice(MOTIVATIONAL_QUOTES)
        return (
            f"Good morning {name}! 💪\n\n"
            f"Rest day from running — gym focus today.\n\n"
            f"_{quote}_"
        )
    else:
        import random
        quote = random.choice(MOTIVATIONAL_QUOTES)
        return (
            f"Good morning {name}! 😴\n\n"
            f"Full rest day today. Recovery is training.\n\n"
            f"_{quote}_"
        )


def send_morning_message():
    cfg = config.load()
    phone = cfg["user"]["phone"]
    if not phone:
        print("⚠️  No phone number configured in config.yaml")
        return

    today = datetime.date.today()
    message = build_morning_message(today)
    success = whatsapp_client.send_message(phone, message)
    if success:
        print(f"✅ Morning message sent for {today}")
    else:
        print(f"❌ Failed to send morning message for {today}")
