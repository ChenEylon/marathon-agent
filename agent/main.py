"""
Marathon Agent — entry point.
Starts the FastAPI server (incoming WhatsApp + Strava webhook)
and the APScheduler (timed jobs) in parallel threads.
"""
import os
import sys
import threading
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import uvicorn
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse

from agent import scheduler as sched
from agent.db import init as db_init
from agent.handlers.post_run import handle_new_activity

app = FastAPI()

WEBHOOK_VERIFY_TOKEN = os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN", "")


# ── WhatsApp incoming ──────────────────────────────────────────────────────────

@app.post("/incoming")
async def incoming_message(request: Request):
    data = await request.json()
    sender = data.get("from", "")
    body   = data.get("body", "").strip()
    print(f"📩 Message from {sender}: {body}")
    # Phase 3 will add Claude-powered reply logic here
    return {"ok": True}


# ── Strava webhook ─────────────────────────────────────────────────────────────

@app.get("/strava/webhook")
def strava_webhook_verify(
    hub_challenge:    str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Strava calls this once to verify our webhook URL."""
    if hub_verify_token != WEBHOOK_VERIFY_TOKEN:
        return JSONResponse(status_code=403, content={"error": "invalid verify token"})
    return {"hub.challenge": hub_challenge}


@app.post("/strava/webhook")
async def strava_webhook_event(request: Request):
    """Strava calls this when an athlete creates/updates an activity."""
    event = await request.json()
    print(f"📡 Strava event: {event}")

    if (
        event.get("object_type") == "activity"
        and event.get("aspect_type") == "create"
    ):
        activity_id = event.get("object_id")
        threading.Thread(target=handle_new_activity, args=(activity_id,), daemon=True).start()

    return {"ok": True}


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Startup ────────────────────────────────────────────────────────────────────

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    db_init()
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("🤖 Marathon Agent started")
    sched.start()  # blocking — keeps the process alive
