"""
Register our server as a Strava webhook subscriber.
Run this once after deploying to the cloud (needs a public URL).

Usage:
    PUBLIC_URL=https://your-server.com python scripts/subscribe_strava_webhook.py
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
VERIFY_TOKEN  = os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN")
PUBLIC_URL    = os.getenv("PUBLIC_URL") or input("Enter your public server URL (e.g. https://your-server.com): ").strip()

if not all([CLIENT_ID, CLIENT_SECRET, VERIFY_TOKEN, PUBLIC_URL]):
    print("❌ Missing one of: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_WEBHOOK_VERIFY_TOKEN, PUBLIC_URL")
    sys.exit(1)

callback_url = f"{PUBLIC_URL.rstrip('/')}/strava/webhook"

resp = requests.post(
    "https://www.strava.com/api/v3/push_subscriptions",
    data={
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "callback_url":  callback_url,
        "verify_token":  VERIFY_TOKEN,
    }
)

if resp.ok:
    sub = resp.json()
    print(f"✅ Webhook registered — subscription ID: {sub.get('id')}")
    print(f"   Strava will POST new activities to: {callback_url}")
else:
    print(f"❌ Failed: {resp.status_code} — {resp.text}")
