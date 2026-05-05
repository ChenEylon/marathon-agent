"""
One-time Google Calendar OAuth authorization.
Requires google_credentials.json downloaded from Google Cloud Console.

Usage:
    python scripts/google_auth.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES           = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_credentials.json")
TOKEN_FILE       = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "google_token.json")

if not os.path.exists(CREDENTIALS_FILE):
    print("❌ google_credentials.json not found.")
    print("   Download it from Google Cloud Console and place it in the marathon-agent folder.")
    print("   See README for setup instructions.")
    sys.exit(1)

os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)

flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
creds = flow.run_local_server(port=0, open_browser=True)

with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())

print(f"✅ Google Calendar authorized. Token saved to {TOKEN_FILE}")
