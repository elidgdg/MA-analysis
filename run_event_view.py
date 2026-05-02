from __future__ import annotations

from pathlib import Path
from pprint import pprint

from ma_index_tracker.db.database import connect
from ma_index_tracker.event_view import build_event_view, save_event_view

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"


def main() -> None:
    event_id = 1

    with connect(DB_PATH) as conn:
        result = build_event_view(conn, event_id)

        summary = {
            "event_id": result["event_id"],
            "target": result["event_summary"]["target_name"],
            "acquirer": result["event_summary"]["acquirer_name"],
            "announcement_date": result["event_summary"]["announcement_date"],
            "expected_completion_date": result["event_summary"]["expected_completion_date"],
            "payment_type": result["event_summary"]["payment_type"],
            "cash_terms_per_tgt_sh": result["event_summary"]["cash_terms_per_tgt_sh"],
            "stock_terms_acq_sh_per_tgt_sh": result["event_summary"]["stock_terms_acq_sh_per_tgt_sh"],
            "headline_metrics": result["headline_metrics"],
            "target_rows_count": len(result["target_analysis"]["rows"]),
            "spread_rows_count": len(result["spread_analysis"]["rows"]),
        }

        print("EVENT VIEW SUMMARY")
        pprint(summary)

        analysis_id = save_event_view(conn, event_id)
        conn.commit()

        print(f"\nSaved event_view in analysis_outputs with id={analysis_id}")


if __name__ == "__main__":
    main()