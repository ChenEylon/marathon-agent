from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent import config
from agent.handlers.morning import send_morning_message


def start():
    cfg = config.load()
    tz = pytz.timezone(cfg["user"]["timezone"])
    message_time = cfg["user"]["message_time"]  # "07:30"
    hour, minute = message_time.split(":")

    scheduler = BlockingScheduler(timezone=tz)

    scheduler.add_job(
        send_morning_message,
        CronTrigger(hour=int(hour), minute=int(minute), timezone=tz),
        id="morning_message",
        name="Daily morning workout message",
    )

    print(f"⏰ Scheduler started — morning message fires at {message_time} ({cfg['user']['timezone']})")
    scheduler.start()
