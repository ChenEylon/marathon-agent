"""
Seeds the database with Chen's 42-week marathon training plan.
Safe to re-run — clears and rebuilds the plan.

Usage:
    python scripts/build_training_plan.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.db import init as db_init, get_connection

def easy(km):        return ("easy",      km, "6:10-6:30", f"Easy run {km}km — fully conversational pace")
def long_(km):       return ("long",      km, "6:10-6:30", f"Long run {km}km — easy pace, walk breaks OK")
def tempo(km, t):    return ("tempo",     km, "5:15-5:30", f"{km}km: 2km warm-up + {t}km tempo (5:15-5:30/km) + cool-down")
def inter(km, reps): return ("intervals", km, "5:45-6:00", f"{km}km: 2km warm-up + {reps}×2km at marathon pace + cool-down")
def race():          return ("race",    42.2, "5:50-6:05", "RACE DAY 🏆 — Marathon 42.2km. Start conservative!")

# (week, phase, monday, wednesday, saturday)
PLAN = [
    # ── Phase 1: Base — weeks 1-14 ───────────────────────────────────────────
    (1,  1, easy(4),   easy(5),      long_(8)),
    (2,  1, easy(4),   easy(5),      long_(9)),
    (3,  1, easy(5),   easy(6),      long_(10)),
    (4,  1, easy(4),   easy(5),      long_(8)),    # cutback
    (5,  1, easy(5),   easy(6),      long_(11)),
    (6,  1, easy(5),   easy(7),      long_(12)),
    (7,  1, easy(6),   easy(7),      long_(13)),
    (8,  1, easy(5),   easy(6),      long_(10)),   # cutback
    (9,  1, easy(6),   easy(8),      long_(14)),
    (10, 1, easy(6),   easy(8),      long_(15)),
    (11, 1, easy(7),   easy(8),      long_(16)),
    (12, 1, easy(6),   easy(7),      long_(12)),   # cutback
    (13, 1, easy(7),   easy(9),      long_(17)),
    (14, 1, easy(7),   easy(9),      long_(18)),

    # ── Phase 2: Build — weeks 15-30 ─────────────────────────────────────────
    (15, 2, easy(7),   tempo(8, 2),  long_(18)),
    (16, 2, easy(7),   tempo(9, 3),  long_(19)),
    (17, 2, easy(7),   tempo(9, 3),  long_(20)),
    (18, 2, easy(6),   easy(7),      long_(14)),   # cutback
    (19, 2, easy(8),   tempo(10, 4), long_(21)),
    (20, 2, easy(8),   tempo(10, 4), long_(22)),   # ← checkpoint half marathon week
    (21, 2, easy(8),   tempo(10, 4), long_(23)),
    (22, 2, easy(7),   easy(8),      long_(16)),   # cutback
    (23, 2, easy(8),   tempo(11, 5), long_(24)),
    (24, 2, easy(9),   tempo(11, 5), long_(25)),
    (25, 2, easy(9),   tempo(11, 5), long_(26)),
    (26, 2, easy(7),   easy(8),      long_(16)),   # cutback
    (27, 2, easy(9),   tempo(12, 6), long_(27)),
    (28, 2, easy(9),   tempo(12, 6), long_(28)),
    (29, 2, easy(9),   tempo(12, 6), long_(26)),
    (30, 2, easy(7),   easy(8),      long_(16)),   # cutback

    # ── Phase 3: Peak — weeks 31-38 ──────────────────────────────────────────
    (31, 3, easy(9),   inter(11, 3), long_(29)),
    (32, 3, easy(9),   inter(12, 3), long_(31)),
    (33, 3, easy(9),   inter(12, 3), long_(33)),   # peak long run
    (34, 3, easy(8),   easy(10),     long_(18)),   # cutback
    (35, 3, easy(9),   inter(12, 3), long_(30)),
    (36, 3, easy(9),   inter(12, 3), long_(32)),
    (37, 3, easy(9),   inter(12, 3), long_(33)),   # peak long run #2
    (38, 3, easy(8),   easy(10),     long_(18)),   # cutback

    # ── Phase 4: Taper — weeks 39-42 ─────────────────────────────────────────
    (39, 4, easy(8),   tempo(10, 4), long_(26)),
    (40, 4, easy(7),   tempo(8, 3),  long_(20)),
    (41, 4, easy(5),   tempo(6, 2),  long_(14)),
    (42, 4, easy(3),   easy(3),      race()),
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
    print(f"   Weeks  1–14: Phase 1 (Base)")
    print(f"   Weeks 15–30: Phase 2 (Build)")
    print(f"   Weeks 31–38: Phase 3 (Peak)")
    print(f"   Weeks 39–42: Phase 4 (Taper)")
    print(f"   Race week:   Week 42 — 26 Feb 2027")

if __name__ == "__main__":
    build()
