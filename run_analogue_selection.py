from __future__ import annotations

from pathlib import Path
from pprint import pprint

from ma_index_tracker.analogues import compute_analogue_selection, save_analogue_selection
from ma_index_tracker.db.database import connect

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"


def main() -> None:
    pending_event_id = 2   # Norfolk / Union Pacific
    top_k = 10

    with connect(DB_PATH) as conn:
        result = compute_analogue_selection(conn, pending_event_id, top_k=top_k)

        print("ANALOGUE SELECTION SUMMARY")
        pprint(
            {
                "pending_event_id": result["pending_event"]["event_id"],
                "pending_target": result["pending_event"]["target_name"],
                "pending_payment_type": result["pending_event"]["payment_type"],
                "pending_sector": result["pending_event"]["target_sector"],
                "pending_announced_total_value_mil": result["pending_event"]["announced_total_value_mil"],
                "candidate_pool_count": result["candidate_pool_count"],
                "top_k": result["top_k"],
            }
        )

        print("\nTOP ANALOGUES")
        for i, analogue in enumerate(result["analogues"], start=1):
            pprint(
                {
                    "rank": i,
                    "event_id": analogue["event_id"],
                    "target_name": analogue["target_name"],
                    "acquirer_name": analogue["acquirer_name"],
                    "announcement_date": analogue["announcement_date"],
                    "payment_type": analogue["payment_type"],
                    "target_sector": analogue["target_sector"],
                    "announced_total_value_mil": analogue["announced_total_value_mil"],
                    "score": analogue["score"],
                    "reasons": analogue["reasons"],
                }
            )

        analysis_id = save_analogue_selection(conn, pending_event_id, top_k=top_k)
        conn.commit()

        print(f"\nSaved analogue_selection in analysis_outputs with id={analysis_id}")


if __name__ == "__main__":
    main()