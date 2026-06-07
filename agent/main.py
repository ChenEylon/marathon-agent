"""
Marathon Agent — entry point.
Starts FastAPI (API + frontend) and APScheduler in parallel threads.
"""
import datetime
import json
import os
import sys
import threading

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agent import scheduler as sched
from agent import training_plan as tp
from agent.db import get_connection, init as db_init
from agent.handlers.post_run import handle_new_activity

app = FastAPI()

WEBHOOK_VERIFY_TOKEN = os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN", "")
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")


# ── Push subscription ──────────────────────────────────────────────────────────

@app.post("/api/subscribe")
async def subscribe(request: Request):
    data = await request.json()
    sub  = data.get("subscription")
    if not sub:
        return JSONResponse(status_code=400, content={"error": "Missing subscription"})
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO push_subscriptions (subscription_json) VALUES (?)",
            (json.dumps(sub),),
        )
        conn.commit()
    return {"ok": True}


@app.get("/api/vapid-public-key")
def vapid_public_key():
    return {"key": os.getenv("VAPID_PUBLIC_KEY", "")}


# ── Message feed ───────────────────────────────────────────────────────────────

@app.get("/api/messages")
def get_messages(limit: int = 60):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM message_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


@app.post("/api/reply")
async def user_reply(request: Request):
    from agent import push_client, config
    data  = await request.json()
    body  = data.get("body", "").strip()
    cfg   = config.load()
    phone = cfg["user"]["phone"]

    with get_connection() as conn:
        conn.execute("INSERT INTO message_log (role, content) VALUES ('user', ?)", (body,))
        conn.commit()

    if body in ("1", "2", "3", "4", "5"):
        feeling = int(body)
        tp.save_feedback(datetime.date.today(), feeling)
        labels = {
            1: "Really tough — noted, I'll factor this in.",
            2: "Hard day — good effort.",
            3: "Solid run!",
            4: "Feeling strong!",
            5: "Easy — I'll push the next one a bit.",
        }
        push_client.send_message(phone, f"Got it — {labels[feeling]} 💪")

    elif body.lower() in ("plan", "תכנית", "סדר יום", "schedule"):
        today        = datetime.date.today()
        current_week = tp.get_current_week(today)
        lines        = [f"📋 *Training Plan — Weeks {current_week}–{min(current_week + 3, 34)}*\n"]
        type_emoji   = {"easy": "🏃", "long": "🏃‍♂️", "tempo": "⚡", "intervals": "🔥", "race": "🏆"}
        for w in range(current_week, min(current_week + 4, 35)):
            workouts = tp.get_week_summary(w)
            if not workouts:
                continue
            week_label = "← this week" if w == current_week else ""
            lines.append(f"*Week {w}* {week_label}")
            for wo in workouts:
                emoji = type_emoji.get(wo["workout_type"], "🏃")
                lines.append(f"  {emoji} {wo['day_of_week'].capitalize()}: {wo['description']} — {wo['distance_km']}km @ {wo['pace_target']}/km")
            lines.append("")
        push_client.send_message(phone, "\n".join(lines))

    return {"ok": True}


# ── AI Coach chat ──────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    from agent.chat import chat
    data    = await request.json()
    message = data.get("message", "").strip()
    if not message:
        return JSONResponse(status_code=400, content={"error": "Empty message"})
    reply = chat(message)
    return {"reply": reply}


@app.get("/api/chat/history")
def chat_history_endpoint():
    from agent.chat import get_history
    return get_history(limit=60)


# ── Strava webhook ─────────────────────────────────────────────────────────────

@app.get("/strava/webhook")
def strava_verify(
    hub_challenge:    str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_verify_token != WEBHOOK_VERIFY_TOKEN:
        return JSONResponse(status_code=403, content={"error": "invalid verify token"})
    return {"hub.challenge": hub_challenge}


@app.post("/strava/webhook")
async def strava_event(request: Request):
    event = await request.json()
    if event.get("object_type") == "activity" and event.get("aspect_type") == "create":
        activity_id = event.get("object_id")
        threading.Thread(target=handle_new_activity, args=(activity_id,), daemon=True).start()
    return {"ok": True}


# ── Training plan ──────────────────────────────────────────────────────────────

_DAY_ORDER = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
_PHASE_NAMES = {0:"Return to Running", 1:"Base Building", 2:"Development", 3:"Peak Training", 4:"Taper"}

@app.get("/api/plan")
def get_plan():
    from agent import config as cfg_mod
    cfg          = cfg_mod.load()
    today        = datetime.date.today()
    current_week = tp.get_current_week(today)
    weeks        = []
    for w in range(current_week, min(current_week + 6, 43)):
        workouts = tp.get_week_summary(w)
        if not workouts:
            continue
        sorted_workouts = sorted([dict(wo) for wo in workouts],
                                 key=lambda x: _DAY_ORDER.get(x["day_of_week"], 9))
        phase = sorted_workouts[0]["phase"]
        weeks.append({
            "week_number":  w,
            "is_current":   w == current_week,
            "phase":        phase,
            "phase_name":   _PHASE_NAMES.get(phase, f"Phase {phase}"),
            "workouts":     sorted_workouts,
        })
    return {
        "current_week": current_week,
        "total_weeks":  42,
        "plan_start":   cfg["training"]["plan_start_date"],
        "weeks":        weeks,
    }


@app.get("/api/activities")
def get_activities(limit: int = 5):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT strava_id, date, distance_km, pace_sec_km, avg_hr "
            "FROM activities ORDER BY date DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/weekly-stats")
def get_weekly_stats():
    from agent import config as cfg_mod
    today        = datetime.date.today()
    current_week = tp.get_current_week(today)
    start_week   = max(1, current_week - 7)
    plan_start   = datetime.date.fromisoformat(cfg_mod.load()["training"]["plan_start_date"])

    with get_connection() as conn:
        planned_rows = conn.execute(
            "SELECT week_number, SUM(distance_km) as total FROM training_plan "
            "WHERE week_number BETWEEN ? AND ? GROUP BY week_number",
            (start_week, current_week),
        ).fetchall()

    planned = {r["week_number"]: r["total"] for r in planned_rows}

    since = (plan_start + datetime.timedelta(weeks=start_week - 1)).isoformat()
    with get_connection() as conn:
        act_rows = conn.execute(
            "SELECT date, distance_km FROM activities WHERE date >= ? ORDER BY date",
            (since,),
        ).fetchall()

    actual: dict[int, float] = {w: 0.0 for w in range(start_week, current_week + 1)}
    for row in act_rows:
        d  = datetime.date.fromisoformat(row["date"])
        wn = max(1, min(42, (d - plan_start).days // 7 + 1))
        if wn in actual:
            actual[wn] += row["distance_km"]

    return {
        "weeks": [
            {"week": w, "planned_km": round(planned.get(w, 0), 1), "actual_km": round(actual.get(w, 0), 1)}
            for w in range(start_week, current_week + 1)
        ]
    }


@app.get("/api/feedback")
def get_feedback_week(week: int = Query(None)):
    if week is None:
        week = tp.get_current_week()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT date, day_of_week, feeling FROM workout_feedback WHERE week_number = ?",
            (week,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/feedback")
async def post_feedback(request: Request):
    data    = await request.json()
    date_s  = data.get("date")
    feeling = data.get("feeling")
    if not date_s or not feeling:
        return JSONResponse(status_code=400, content={"error": "Missing date or feeling"})
    tp.save_feedback(datetime.date.fromisoformat(date_s), int(feeling))
    return {"ok": True}


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Frontend (PWA) ─────────────────────────────────────────────────────────────

if os.path.exists(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/sw.js")
    def service_worker():
        return FileResponse(os.path.join(FRONTEND_DIST, "sw.js"), media_type="application/javascript")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Serve specific files if they exist, otherwise fall back to index.html (SPA)
        target = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
else:
    @app.get("/")
    def no_frontend():
        return {"message": "Frontend not built yet. Run: cd frontend && npm run build"}


# ── Startup ────────────────────────────────────────────────────────────────────

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    db_init()
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("🤖 Marathon Agent started — http://localhost:8000")
    sched.start()
