from pathlib import Path
from ma_index_tracker.db.database import connect

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"

def main() -> None:
    with connect(DB_PATH) as conn:
        conn.execute("DELETE FROM companies WHERE ticker = ?", ("AAPL",))
        conn.commit()
    print("Deleted AAPL")

if __name__ == "__main__":
    main()