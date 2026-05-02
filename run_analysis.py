from __future__ import annotations

from pathlib import Path
from pprint import pprint

from ma_index_tracker.analysis import compute_target_analysis, save_target_analysis
from ma_index_tracker.db.database import connect

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"


def main() -> None:
    event_id = 1

    with connect(DB_PATH) as conn:
        result = compute_target_analysis(conn, event_id)

        summary = {
            "event_id": result["event_id"],
            "target_ticker": result["target_ticker"],
            "announcement_date": result["announcement_date"],
            "baseline_date": result["baseline_date"],
            "baseline_price": result["baseline_price"],
            "announcement_trading_date": result["announcement_trading_date"],
            "announcement_day_price": result["announcement_day_price"],
            "announcement_jump": result["announcement_jump"],
            "avg_pre_announcement_volume": result["avg_pre_announcement_volume"],
            "row_count": len(result["rows"]),
        }

        print("TARGET ANALYSIS SUMMARY")
        pprint(summary)

        analysis_id = save_target_analysis(conn, event_id)
        conn.commit()

        print(f"\nSaved target_analysis in analysis_outputs with id={analysis_id}")


if __name__ == "__main__":
    main()