from pathlib import Path
from ma_index_tracker.db.database import init_db

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"

init_db(DB_PATH)
print(f"Schema upgrade applied to {DB_PATH}")