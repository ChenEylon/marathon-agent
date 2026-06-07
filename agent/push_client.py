import json
import os
from agent.db import get_connection

VAPID_PRIVATE_KEY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "vapid_private.pem"
)
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_EMAIL      = os.getenv("VAPID_EMAIL", "mailto:admin@localhost")


def send_message(_to: str, message: str) -> bool:
    """Send push notification to all subscribed devices. _to is kept for compat with whatsapp_client."""
    _log_message("agent", message)

    if not os.path.exists(VAPID_PRIVATE_KEY_PATH):
        print("⚠️  VAPID private key not found — message logged only. Run scripts/gen_vapid.py")
        return True

    subscriptions = _get_subscriptions()
    if not subscriptions:
        print("⚠️  No push subscriptions yet — message logged, waiting for first browser visit")
        return True

    from pywebpush import webpush, WebPushException
    ok = True
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=json.loads(sub["subscription_json"]),
                data=json.dumps({
                    "title": "Marathon Coach 🏃",
                    "body": message[:120],
                    "full": message,
                }),
                vapid_private_key=VAPID_PRIVATE_KEY_PATH,
                vapid_claims={"sub": VAPID_EMAIL},
                ttl=86400,
            )
        except WebPushException as e:
            code = str(e)
            print(f"Push failed (sub {sub['id']}): {code}")
            if "410" in code or "404" in code:
                _remove_subscription(sub["id"])
            ok = False
    return ok


def is_connected() -> bool:
    return True


def _log_message(role: str, content: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO message_log (role, content) VALUES (?, ?)",
            (role, content),
        )
        conn.commit()


def _get_subscriptions() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT id, subscription_json FROM push_subscriptions").fetchall()
    return [dict(r) for r in rows]


def _remove_subscription(sub_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM push_subscriptions WHERE id = ?", (sub_id,))
        conn.commit()
