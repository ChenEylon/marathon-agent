"""
Seeds the database with Chen's 34-week marathon training plan.
Safe to re-run — clears and rebuilds the plan.

Usage:
    python scripts/build_training_plan.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.db import init as db_init, get_connection

EASY   = ("easy",  "6:10-6:30", "Easy run — fully conversational pace")
LONG   = ("long",  "6:10-6:30", "Long run — easy pace throughout, walk breaks OK")
TEMPO  = ("tempo", "5:15-5:30", "{km}km total: 2km warm-up + {t}km tempo (5:15-5:30/km) + cool-down")
INTER  = ("intervals", "5:45-6:00", "{km}km total: 2km warm-up + {reps}×2km at marathon pace (5:45-6:00/km) + cool-down")
RACE   = ("race",  "5:50-6:05", "RACE DAY 🏆 — Marathon 42.2km. Start conservative, negative split!")

def easy(km):   return ("easy",  km, "6:10-6:30", f"Easy run {km}km — fully conversational pace")
def long_(km):  return ("long",  km, "6:10-6:30", f"Long run {km}km — easy pace, walk breaks OK")
def tempo(km, t): return ("tempo", km, "5:15-5:30", f"{km}km: 2km warm-up + {t}km tempo (5:15-5:30/km) + cool-down")
def inter(km, reps): return ("intervals", km, "5:45-6:00", f"{km}km: 2km warm-up + {reps}×2km at marathon pace + cool-down")
def race():     return ("race",  42.2, "5:50-6:05", "RACE DAY 🏆 — Marathon 42.2km. Start conservative!")

# (week, phase, monday, wednesday, saturday)
PLAN = [
    # ── Phase 1: Base — easy running only, rebuild base safely ───────────────
    (1,  1, easy(4),   easy(5),      long_(8)),
    (2,  1, easy(4),   easy(5),      long_(9)),
    (3,  1, easy(5),   easy(6),      long_(10)),
    (4,  1, easy(4),   easy(5),      long_(8)),    # cutback week
    (5,  1, easy(5),   easy(6),      long_(11)),
    (6,  1, easy(5),   easy(7),      long_(12)),
    (7,  1, easy(6),   easy(7),      long_(13)),
    (8,  1, easy(5),   easy(6),      long_(10)),   # cutback week
    (9,  1, easy(6),   easy(8),      long_(14)),
    (10, 1, easy(6),   easy(8),      long_(15)),

    # ── Phase 2: Build — introduce tempo on Wednesdays ────────────────────────
    (11, 2, easy(6),   tempo(8, 2),  long_(16)),
    (12, 2, easy(7),   tempo(9, 3),  long_(17)),
    (13, 2, easy(7),   tempo(9, 3),  long_(18)),
    (14, 2, easy(6),   easy(7),      long_(14)),   # cutback week
    (15, 2, easy(7),   tempo(10, 4), long_(19)),
    (16, 2, easy(8),   tempo(10, 4), long_(20)),   # ← checkpoint half marathon
    (17, 2, easy(7),   tempo(10, 4), long_(21)),
    (18, 2, easy(6),   easy(7),      long_(14)),   # cutback week
    (19, 2, easy(8),   tempo(11, 5), long_(22)),
    (20, 2, easy(8),   tempo(11, 5), long_(23)),
    (21, 2, easy(8),   tempo(11, 5), long_(24)),
    (22, 2, easy(7),   easy(8),      long_(16)),   # cutback week

    # ── Phase 3: Peak — long runs to 33km, add marathon-pace intervals ────────
    (23, 3, easy(8),   tempo(12, 6), long_(25)),
    (24, 3, easy(9),   tempo(12, 6), long_(26)),
    (25, 3, easy(9),   inter(11, 3), long_(27)),
    (26, 3, easy(8),   easy(10),     long_(18)),   # cutback week
    (27, 3, easy(9),   inter(12, 3), long_(29)),
    (28, 3, easy(9),   inter(12, 3), long_(31)),
    (29, 3, easy(9),   inter(12, 3), long_(33)),   # peak long run
    (30, 3, easy(8),   easy(10),     long_(18)),   # cutback week

    # ── Phase 4: Taper — reduce volume, stay sharp ────────────────────────────
    (31, 4, easy(8),   tempo(10, 4), long_(26)),
    (32, 4, easy(7),   tempo(8, 3),  long_(20)),
    (33, 4, easy(5),   tempo(6, 2),  long_(14)),
    (34, 4, easy(3),   easy(3),      race()),
]

def build():
    db_init()
    with get_connection() as conn:
        conn.execute("DELETE FROM training_plan")
        for row in PLAN:
            week, phase = row[0], row[1]
            for day, workout in zip(("monday", "wednesday", "saturday"), row[2:]):
                wtype, km, pace, desc = workout
                conn.execute("""
                    INSERT INTO training_plan
                        (week_number, day_of_week, phase, workout_type, distance_km, pace_target, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (week, day, phase, wtype, km, pace, desc))
        conn.commit()
    print(f"✅ Training plan built — {len(PLAN) * 3} workouts seeded into DB")
    print(f"   Weeks 1–10:  Phase 1 (Base)")
    print(f"   Weeks 11–22: Phase 2 (Build)")
    print(f"   Weeks 23–30: Phase 3 (Peak)")
    print(f"   Weeks 31–34: Phase 4 (Taper)")

if __name__ == "__main__":
    build()
