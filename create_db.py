from __future__ import annotations

from pathlib import Path

from ma_index_tracker.db.database import init_db


def main() -> None:
    """Initialise the SQLite database schema only."""
    database_path = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"
    init_db(database_path)
    print(f"Initialised database at {database_path}")


if __name__ == "__main__":
    main()