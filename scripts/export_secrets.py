#!/usr/bin/env python3
"""
Print all credentials as base64 env var strings ready to paste into Koyeb.
Run once locally after authenticating all services:
  source venv/bin/activate && python scripts/export_secrets.py
"""
import base64, json, os, sqlite3, sys, tarfile, io
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DATA     = ROOT / "data"
DB_PATH  = DATA / "data.db"

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()

print("# Paste these into Koyeb → Service → Environment variables\n")

# Strava tokens from DB
if DB_PATH.exists():
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute("SELECT access_token, refresh_token, expires_at FROM strava_tokens WHERE id=1").fetchone()
    conn.close()
    if row:
        print(f"STRAVA_ACCESS_TOKEN={row[0]}")
        print(f"STRAVA_REFRESH_TOKEN={row[1]}")
        print(f"STRAVA_EXPIRES_AT={row[2]}")
    else:
        print("# WARNING: no Strava tokens in DB — run scripts/strava_auth.py first", file=sys.stderr)

# Garmin tokens (directory → tar.gz → base64)
garth_dir = DATA / "garth_tokens"
if garth_dir.exists():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(garth_dir, arcname="garth_tokens")
    print(f"GARTH_TOKENS_B64={b64(buf.getvalue())}")
else:
    print("# WARNING: no Garmin tokens — run scripts/garmin_auth.py first", file=sys.stderr)

# Google Calendar token
google_token = DATA / "google_token.json"
if google_token.exists():
    print(f"GOOGLE_TOKEN_B64={b64(google_token.read_bytes())}")
else:
    print("# WARNING: no Google token — run scripts/google_auth.py first", file=sys.stderr)

# VAPID private key
vapid_key = DATA / "vapid_private.pem"
if vapid_key.exists():
    print(f"VAPID_PRIVATE_KEY_B64={b64(vapid_key.read_bytes())}")
else:
    print("# WARNING: no VAPID key — run scripts/gen_vapid.py first", file=sys.stderr)
