"""
Simulate week 5 results and post the Punter Report to the shadow/test group.
Inserts temporary results, generates + sends the report, then removes them.

Usage: venv/bin/python3 scripts/simulate_report_wk5.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import requests

DB_PATH = "data/punter_bot.db"
GROUP_ID = os.getenv("GROUP_CHAT_ID", "your-group-id@g.us")
SEASON = "2026"
END_WEEK = 5

# Simulated outcomes for week 5 picks (pick_id → outcome)
# Mr Aidan  - Newcastle vs Sunderland Over 5.5 Cards  → LOSS (cards market, tight)
# Mr Declan - Fulham                                   → WIN
# Mr Edmund - SHU/Wrexham BTTS                        → WIN
# Mr Kevin  - mayo football                            → WIN
# Mr Niall  - Plymouth                                 → LOSS
# Mr Ronan  - Everton +1 vs Chelsea                   → LOSS
SIMULATED = {
    29: "loss",   # Mr Aidan
    30: "win",    # Mr Declan
    28: "win",    # Mr Edmund
    31: "win",    # Mr Kevin
    33: "loss",   # Mr Niall
    32: "loss",   # Mr Ronan
}

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Insert simulated results
    inserted_ids = []
    for pick_id, outcome in SIMULATED.items():
        conn.execute(
            "INSERT INTO results (pick_id, outcome, confirmed_by, confirmed_at) "
            "VALUES (?, ?, 'simulate_script', datetime('now'))",
            (pick_id, outcome),
        )
        row = conn.execute("SELECT last_insert_rowid() as id").fetchone()
        inserted_ids.append(row["id"])
    conn.commit()
    print(f"Inserted {len(inserted_ids)} simulated results (ids: {inserted_ids})")

    try:
        # Generate the report
        from src.services.report_service import get_period_data
        import src.butler as butler

        data = get_period_data(SEASON, END_WEEK, GROUP_ID)

        # Week 1 was stored under group_id 'default' — merge it in if needed
        if not any(r["week_number"] == 1 for r in data["player_rows"]):
            data_default = get_period_data(SEASON, END_WEEK, "default")
            wk1_rows = [r for r in data_default["player_rows"] if r["week_number"] == 1]
            data["player_rows"] = wk1_rows + data["player_rows"]
            data["start_week"] = 1

        print(f"\nPeriod: weeks {data['start_week']}–{data['end_week']}, {len(data['player_rows'])} pick rows")

        text = butler.punter_report_display(data)
        print("\n--- REPORT ---")
        print(text)
        print("--------------")

        # Send to shadow group via bridge
        from src.config import Config
        shadow_id = Config.SHADOW_GROUP_ID
        bridge = Config.BRIDGE_URL

        resp = requests.post(
            f"{bridge}/send",
            json={"chat_id": shadow_id, "message": text},
            timeout=15,
        )
        if resp.status_code == 200:
            print(f"\nPosted to shadow group {shadow_id}")
        else:
            print(f"\nBridge returned {resp.status_code}: {resp.text[:200]}")

    finally:
        # Clean up: remove simulated results
        conn.execute(
            f"DELETE FROM results WHERE id IN ({','.join('?' * len(inserted_ids))})",
            inserted_ids,
        )
        conn.commit()
        conn.close()
        print(f"Cleaned up {len(inserted_ids)} simulated results")


if __name__ == "__main__":
    main()
