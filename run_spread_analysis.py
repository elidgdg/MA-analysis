from __future__ import annotations

from pathlib import Path
from pprint import pprint

from ma_index_tracker.db.database import connect
from ma_index_tracker.spread_analysis import compute_spread_analysis, save_spread_analysis

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"


def main() -> None:
    event_id = 1

    with connect(DB_PATH) as conn:
        result = compute_spread_analysis(conn, event_id)

        summary = {
            "event_id": result["event_id"],
            "bbg_deal_id": result["bbg_deal_id"],
            "payment_type": result["payment_type"],
            "cash_terms_per_tgt_sh": result["cash_terms_per_tgt_sh"],
            "stock_terms_acq_sh_per_tgt_sh": result["stock_terms_acq_sh_per_tgt_sh"],
            "announcement_day_spread_abs": result["announcement_day_spread_abs"],
            "announcement_day_spread_pct": result["announcement_day_spread_pct"],
            "day_5_spread_abs": result["day_5_spread_abs"],
            "day_5_spread_pct": result["day_5_spread_pct"],
            "latest_spread_abs": result["latest_spread_abs"],
            "latest_spread_pct": result["latest_spread_pct"],
            "row_count": len(result["rows"]),
        }

        print("SPREAD ANALYSIS SUMMARY")
        pprint(summary)

        analysis_id = save_spread_analysis(conn, event_id)
        conn.commit()

        print(f"\nSaved spread_analysis in analysis_outputs with id={analysis_id}")


if __name__ == "__main__":
    main()