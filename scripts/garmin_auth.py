"""
First-time Garmin Connect authentication.
Saves OAuth tokens so the agent can pull HRV and Body Battery daily.

Usage:
    python scripts/garmin_auth.py
"""
import os
import sys
import garminconnect

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

TOKENSTORE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "garth_tokens")
os.makedirs(TOKENSTORE, exist_ok=True)

email    = os.getenv("GARMIN_EMAIL") or input("Garmin Connect email: ").strip()
password = os.getenv("GARMIN_PASSWORD") or input("Garmin Connect password: ").strip()


def prompt_mfa():
    code = os.getenv("GARMIN_MFA_CODE", "").strip()
    if code:
        print(f"Using MFA code: {code}")
        return code
    return input("Garmin MFA code: ").strip()


print("\nLogging in to Garmin Connect...")

try:
    api = garminconnect.Garmin(email, password, prompt_mfa=prompt_mfa)
    api.login(tokenstore=TOKENSTORE)
    print(f"✅ Authenticated successfully")
    print(f"   Tokens saved to {TOKENSTORE}")
except Exception as e:
    print(f"❌ Login failed: {e}")
    sys.exit(1)
