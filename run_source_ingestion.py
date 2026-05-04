from __future__ import annotations

import argparse
import time
from pathlib import Path

from ma_index_tracker.db.database import connect, init_db
from ma_index_tracker.source_ingestion import get_pending_event_ids, insert_sources

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"
MAX_RECORDS_PER_EVENT = 20
SLEEP_SECONDS_BETWEEN_EVENTS = 5.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch simple public headline/link sources for M&A events."
    )
    parser.add_argument(
        "--event-id",
        type=int,
        help="Only ingest sources for one event. Defaults to all pending events.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    init_db(DB_PATH)

    with connect(DB_PATH) as conn:
        event_ids = [args.event_id] if args.event_id is not None else get_pending_event_ids(conn)

        for idx, event_id in enumerate(event_ids):
            if idx > 0:
                time.sleep(SLEEP_SECONDS_BETWEEN_EVENTS)

            try:
                sources = insert_sources(
                    conn,
                    event_id,
                    max_records=MAX_RECORDS_PER_EVENT,
                    top_n=3,
                )
            except Exception as exc:
                print(f"event_id={event_id}: failed: {exc}")
                continue

            conn.commit()
            print(f"event_id={event_id}: saved {len(sources)} source(s)")
            for source in sources:
                print(f"  - {source.title} ({source.publisher})")


if __name__ == "__main__":
    main()
