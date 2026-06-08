#!/usr/bin/env python3
"""
Restore credentials from env vars into /app/data at container startup.
Called by the Docker CMD before starting the agent.
"""
import base64, io, os, sqlite3, sys, tarfile
from pathlib import Path

DATA = Path(os.getenv("DATA_DIR", "/app/data"))
DATA.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA / "data.db"

errors = []

def b64dec(val: str) -> bytes:
    return base64.b64decode(val)

# ── Strava tokens ─────────────────────────────────────────────────────────────
access  = os.getenv("STRAVA_ACCESS_TOKEN")
refresh = os.getenv("STRAVA_REFRESH_TOKEN")
expires = os.getenv("STRAVA_EXPIRES_AT")
if access and refresh and expires:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS strava_tokens (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        INSERT INTO strava_tokens (id, access_token, refresh_token, expires_at)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            access_token  = excluded.access_token,
            refresh_token = excluded.refresh_token,
            expires_at    = excluded.expires_at
    """, (access, refresh, int(expires)))
    conn.commit()
    conn.close()
    print("✅ Strava tokens restored")
else:
    errors.append("STRAVA_ACCESS_TOKEN / STRAVA_REFRESH_TOKEN / STRAVA_EXPIRES_AT")

# ── Garmin tokens ──────────────────────────────────────────────────────────────
garth_b64 = os.getenv("GARTH_TOKENS_B64")
if garth_b64:
    try:
        buf = io.BytesIO(b64dec(garth_b64))
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            tar.extractall(DATA)
        print("✅ Garmin tokens restored")
    except Exception as e:
        errors.append(f"GARTH_TOKENS_B64 (corrupt: {e})")
else:
    errors.append("GARTH_TOKENS_B64")

# ── Google Calendar token ──────────────────────────────────────────────────────
google_b64 = os.getenv("GOOGLE_TOKEN_B64")
if google_b64:
    (DATA / "google_token.json").write_bytes(b64dec(google_b64))
    print("✅ Google token restored")
else:
    errors.append("GOOGLE_TOKEN_B64")

# ── VAPID private key ──────────────────────────────────────────────────────────
vapid_b64 = os.getenv("VAPID_PRIVATE_KEY_B64")
if vapid_b64:
    (DATA / "vapid_private.pem").write_bytes(b64dec(vapid_b64))
    print("✅ VAPID key restored")
else:
    errors.append("VAPID_PRIVATE_KEY_B64")

if errors:
    print(f"⚠️  Missing env vars (some features may not work): {', '.join(errors)}", file=sys.stderr)

print("✅ init_data done")
