from pathlib import Path
from ma_index_tracker.db.database import connect

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"

with connect(DB_PATH) as conn:
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    print("TABLES")
    for row in tables:
        print(row["name"])

    print("\nEVENT_SOURCES EXISTS?")
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='event_sources'"
    ).fetchone()
    print(bool(row))