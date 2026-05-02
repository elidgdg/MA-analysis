from __future__ import annotations

import json
from pathlib import Path
from pprint import pprint

from ma_index_tracker.bulk_loader import load_many_deals

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "ma_index_tracker.sqlite"
DATA_DIR = PROJECT_ROOT / "data"

PENDING_CSV = DATA_DIR / "pending_deals.csv"
COMPLETED_CSV = DATA_DIR / "completed_deals.csv"
FAILED_OUTPUT = PROJECT_ROOT / "failed_deal_loads.json"


def main() -> None:
    # Optional manual overrides if any name->ticker resolutions fail.
    # Add entries only when needed.
    ticker_overrides = {
        # "Warner Bros Discovery Inc": "WBD US Equity",
        # "Paramount Skydance Corp": "??? US Equity",
    }

    result = load_many_deals(
        db_path=DB_PATH,
        csv_paths=[PENDING_CSV, COMPLETED_CSV],
        ticker_overrides=ticker_overrides,
        market_end_date=None,
    )

    summary = {
        "total_rows": result["total_rows"],
        "loaded_count": result["loaded_count"],
        "failed_count": result["failed_count"],
    }

    print("\nLOAD SUMMARY")
    pprint(summary)

    if result["failed"]:
        with FAILED_OUTPUT.open("w", encoding="utf-8") as f:
            json.dump(result["failed"], f, indent=2)
        print(f"\nWrote failed rows to: {FAILED_OUTPUT}")
    else:
        print("\nNo failed rows.")


if __name__ == "__main__":
    main()