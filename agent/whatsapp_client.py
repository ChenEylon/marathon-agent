import requests
import os

BRIDGE_URL = os.getenv("BRIDGE_URL", "http://localhost:3000")


def send_message(phone: str, message: str) -> bool:
    try:
        resp = requests.post(
            f"{BRIDGE_URL}/send",
            json={"to": phone, "message": message},
            timeout=10,
        )
        return resp.ok
    except requests.RequestException as e:
        print(f"WhatsApp send failed: {e}")
        return False


def is_connected() -> bool:
    try:
        resp = requests.get(f"{BRIDGE_URL}/health", timeout=5)
        return resp.json().get("ready", False)
    except requests.RequestException:
        return False
