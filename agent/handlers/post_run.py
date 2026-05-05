from agent import whatsapp_client, config, strava

RUN_TYPES = {"Run", "VirtualRun", "TrailRun"}


def _pace_str(speed_ms: float) -> str:
    if speed_ms <= 0:
        return "N/A"
    secs = 1000 / speed_ms
    return f"{int(secs // 60)}:{int(secs % 60):02d}"


def handle_new_activity(activity_id: int):
    cfg = config.load()
    phone = cfg["user"]["phone"]
    name  = cfg["user"]["name"]

    activity = strava.get_activity(activity_id)

    if activity.get("type") not in RUN_TYPES:
        return

    strava.save_activity(activity)

    distance_km = round(activity.get("distance", 0) / 1000, 2)
    avg_pace    = _pace_str(activity.get("average_speed", 0))
    avg_hr      = activity.get("average_heartrate")
    effort      = activity.get("suffer_score")
    elapsed_min = int(activity.get("elapsed_time", 0) // 60)

    lines = [
        f"Great run, {name}! 🏃\n",
        f"📏 Distance: {distance_km}km",
        f"⏱️ Avg pace: {avg_pace}/km",
        f"🕐 Duration: {elapsed_min} min",
    ]
    if avg_hr:
        lines.append(f"❤️ Avg HR: {int(avg_hr)} bpm")
    if effort:
        lines.append(f"💪 Relative effort: {int(effort)}")

    lines.append("\nData saved. Adaptive analysis will factor this into your next workout.")

    whatsapp_client.send_message(phone, "\n".join(lines))
    print(f"✅ Post-run message sent — activity {activity_id} ({distance_km}km)")
