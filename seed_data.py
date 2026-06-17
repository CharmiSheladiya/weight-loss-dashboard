"""
seed_data.py
Optional helper script to populate the database with realistic sample
history so the Dashboard, Analytics, and Reports pages have something to
display immediately. Safe to run multiple times (it skips dates that
already have a logged weight).

Run with:
    python seed_data.py

This is OPTIONAL — the app works perfectly with zero data (you'll just see
empty-state charts until you log your first entry in Daily Tracker).
To remove sample data, delete data/weight_tracker.db and restart the app.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import database as db

random.seed(42)


def run():
    db.init_db()
    profile = db.get_profile()
    start_weight = float(profile["start_weight_kg"])  # 64.0
    goal_weight = float(profile["goal_weight_kg"])     # 50.0

    days = 60
    today = date.today()
    start_date = today - timedelta(days=days)

    total_target_loss = start_weight - goal_weight
    daily_rate = (total_target_loss / 365.0) * 0.55  # realistic partial pace for demo

    current = start_weight
    inserted = 0

    for i in range(days + 1):
        log_date = start_date + timedelta(days=i)
        existing = db.get_log_for_date(log_date)
        if existing is not None and existing["weight_kg"] is not None:
            continue  # don't overwrite real user data

        noise = random.uniform(-0.25, 0.25)
        current = max(current - daily_rate + noise, goal_weight - 1)

        steps = random.randint(4500, 9500)
        walking_minutes = round(steps / 110, 1)
        calories = random.randint(1450, 1850)
        protein = random.randint(55, 95)
        water = random.randint(1800, 2900)

        notes_pool = [
            "Tea with 240ml non-fat milk + monk fruit. Dhokla breakfast.",
            "Khichdi dinner, light snack of roasted chana.",
            "20 min gentle yoga, knees felt good today.",
            "Walking pad session split into two 15-min blocks.",
            "Thepla breakfast, dal-bhaat dinner, fruit snack.",
            "Slightly low energy today, kept walk short.",
            "Treadmill incline walk 25 minutes.",
            "Handvo breakfast, moong dal dinner.",
            "",
        ]

        db.upsert_daily_log(
            log_date=log_date,
            weight_kg=round(current, 1),
            steps=steps,
            calories=calories,
            protein_g=protein,
            water_ml=water,
            walking_minutes=walking_minutes,
            notes=random.choice(notes_pool) or None,
        )
        inserted += 1

    print(f"Seed complete. Inserted/updated {inserted} day(s) of sample data.")
    print(f"Database location: {db.get_db_path()}")


if __name__ == "__main__":
    run()
