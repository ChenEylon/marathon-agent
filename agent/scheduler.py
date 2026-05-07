from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent import config
from agent.handlers.morning import send_morning_message
from agent.handlers.deadline import check_and_send_deadline_reminders
from agent.handlers.weekly_review import run_weekly_review


def start():
    cfg          = config.load()
    tz           = pytz.timezone(cfg["user"]["timezone"])
    message_time = cfg["user"]["message_time"]
    hour, minute = message_time.split(":")

    scheduler = BlockingScheduler(timezone=tz)

    scheduler.add_job(
        send_morning_message,
        CronTrigger(hour=int(hour), minute=int(minute), timezone=tz),
        id="morning_message",
        name="Daily morning workout message",
    )

    # Deadline check fires 30 minutes after the morning message
    deadline_hour   = int(hour)
    deadline_minute = int(minute) + 30
    if deadline_minute >= 60:
        deadline_hour   += 1
        deadline_minute -= 60

    scheduler.add_job(
        check_and_send_deadline_reminders,
        CronTrigger(hour=deadline_hour, minute=deadline_minute, timezone=tz),
        id="deadline_check",
        name="Daily academic deadline reminders",
    )

    # Weekly review every Monday at 07:00 (before morning message)
    scheduler.add_job(
        run_weekly_review,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=tz),
        id="weekly_review",
        name="Weekly pace recalibration",
    )

    print(f"⏰ Scheduler started")
    print(f"   Morning message:   {hour}:{minute} ({cfg['user']['timezone']})")
    print(f"   Deadline check:    {deadline_hour}:{deadline_minute:02d} ({cfg['user']['timezone']})")
    print(f"   Weekly review:     Monday 07:00 ({cfg['user']['timezone']})")
    scheduler.start()
