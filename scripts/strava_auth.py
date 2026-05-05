"""
One-time Strava OAuth setup.
Run this once to authorize the agent and store your tokens.

Usage:
    python scripts/strava_auth.py
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.db import init as db_init, get_connection

CLIENT_ID     = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in your .env file first.")
    sys.exit(1)

db_init()

auth_url = (
    f"https://www.strava.com/oauth/authorize"
    f"?client_id={CLIENT_ID}"
    f"&redirect_uri=http://localhost"
    f"&response_type=code"
    f"&scope=activity:read_all"
)

print("\n1. Open this URL in your browser:\n")
print(f"   {auth_url}\n")
print("2. Authorize the app.")
print("3. You'll be redirected to http://localhost?...&code=XXXXXXXX")
print("   (the page won't load — that's fine)")
print("4. Copy the full URL from your browser's address bar and paste it here.\n")

redirect_url = input("Paste the redirect URL: ").strip()

try:
    code = [p.split("=")[1] for p in redirect_url.split("?")[1].split("&") if p.startswith("code=")][0]
except (IndexError, KeyError):
    print("❌ Couldn't parse the code from that URL.")
    sys.exit(1)

resp = requests.post("https://www.strava.com/oauth/token", data={
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code":          code,
    "grant_type":    "authorization_code",
})

if not resp.ok:
    print(f"❌ Token exchange failed: {resp.text}")
    sys.exit(1)

data = resp.json()
with get_connection() as conn:
    conn.execute("""
        INSERT INTO strava_tokens (id, access_token, refresh_token, expires_at)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            access_token  = excluded.access_token,
            refresh_token = excluded.refresh_token,
            expires_at    = excluded.expires_at
    """, (data["access_token"], data["refresh_token"], data["expires_at"]))
    conn.commit()

athlete = data.get("athlete", {})
print(f"\n✅ Authorized! Welcome, {athlete.get('firstname', 'athlete')}.")
print("Tokens saved to data.db — you're ready to run the agent.")
