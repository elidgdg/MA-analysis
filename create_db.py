from __future__ import annotations

from ma_index_tracker.db.database import init_db, upsert_company, connect


def main() -> None:
    """Initialise the configured SQLite database."""

    database_path = "ma_index_tracker.sqlite"
    init_db(database_path)

    with connect(database_path) as conn:
        upsert_company(
            conn=conn,
            ticker="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            country="USA",
            sector="Technology"
        )
        row = conn.execute("SELECT * FROM companies WHERE ticker = ?", ("AAPL",)).fetchone()
        print(dict(row))

    print(f"Initialised database at {database_path}")


if __name__ == "__main__":
    main()
