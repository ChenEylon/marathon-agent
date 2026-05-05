"""
Marathon Agent — entry point.
Starts the FastAPI server (for incoming WhatsApp messages)
and the APScheduler (for timed jobs) in parallel.
"""
import threading
import uvicorn
from fastapi import FastAPI, Request

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent import scheduler as sched

app = FastAPI()


@app.post("/incoming")
async def incoming_message(request: Request):
    data = await request.json()
    sender = data.get("from", "")
    body = data.get("body", "")
    print(f"📩 Message from {sender}: {body}")
    # Phase 3 will add Claude-powered reply logic here
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("🤖 Marathon Agent started")
    sched.start()  # blocking — keeps the process alive
