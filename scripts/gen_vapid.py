#!/usr/bin/env python3
"""Generate VAPID keys for Web Push notifications and save to .env"""
import os
import sys
import base64
import re

ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(ROOT, "data")
ENV_FILE    = os.path.join(ROOT, ".env")
KEY_PATH    = os.path.join(DATA_DIR, "vapid_private.pem")

sys.path.insert(0, os.path.join(ROOT, "venv", "lib"))

try:
    from py_vapid import Vapid
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
except ImportError:
    print("Activate venv first: source venv/bin/activate")
    sys.exit(1)

os.makedirs(DATA_DIR, exist_ok=True)

v = Vapid()
v.generate_keys()
v.save_key(KEY_PATH)

public_bytes = v.public_key.public_bytes(encoding=Encoding.X962, format=PublicFormat.UncompressedPoint)
public_b64   = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode()

print(f"✅ Private key: {KEY_PATH}")
print(f"✅ Public key:  {public_b64}")

with open(ENV_FILE, "r") as f:
    content = f.read()

def set_env(text: str, key: str, value: str) -> str:
    if re.search(rf"^{key}=", text, re.MULTILINE):
        return re.sub(rf"^{key}=.*", f"{key}={value}", text, flags=re.MULTILINE)
    return text + f"\n{key}={value}\n"

content = set_env(content, "VAPID_PUBLIC_KEY", public_b64)

garmin_email = os.getenv("GARMIN_EMAIL", "admin@localhost")
content = set_env(content, "VAPID_EMAIL", f"mailto:{garmin_email}")

# Remove old BRIDGE_URL if present
content = re.sub(r"^BRIDGE_URL=.*\n?", "", content, flags=re.MULTILINE)

with open(ENV_FILE, "w") as f:
    f.write(content)

print("✅ .env updated")
print("\nNext: start the agent with: source venv/bin/activate && python agent/main.py")
