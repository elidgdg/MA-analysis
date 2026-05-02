from __future__ import annotations

from pathlib import Path
from pprint import pprint

from ma_index_tracker.comparison import (
    compute_analogue_comparison,
    save_analogue_comparison,
)
from ma_index_tracker.db.database import connect

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"


def main() -> None:
    pending_event_id = 2   # Norfolk / Union Pacific
    top_k = 10
    min_event_day = -5
    max_event_day = 60

    with connect(DB_PATH) as conn:
        result = compute_analogue_comparison(
            conn,
            pending_event_id,
            top_k=top_k,
            min_event_day=min_event_day,
            max_event_day=max_event_day,
        )

        print("ANALOGUE COMPARISON SUMMARY")
        pprint(
            {
                "pending_event_id": result["pending_event_id"],
                "pending_target": result["analogue_selection"]["pending_event"]["target_name"],
                "pending_payment_type": result["analogue_selection"]["pending_event"]["payment_type"],
                "candidate_pool_count": result["analogue_selection"]["candidate_pool_count"],
                "tier_1_same_sector_count": result["analogue_selection"]["tier_1_same_sector_count"],
                "tier_2_fallback_count": result["analogue_selection"]["tier_2_fallback_count"],
                "selected_analogue_count": len(result["analogue_selection"]["analogues"]),
                "comparison_window": result["comparison_window"],
            }
        )

        print("\nHEADLINE COMPARISON")
        pprint(result["headline_comparison"])

        print("\nTOP ANALOGUES USED")
        for i, analogue in enumerate(result["analogue_selection"]["analogues"], start=1):
            pprint(
                {
                    "rank": i,
                    "event_id": analogue["event_id"],
                    "target_name": analogue["target_name"],
                    "announcement_date": analogue["announcement_date"],
                    "tier": analogue["tier"],
                    "score": analogue["score"],
                    "reasons": analogue["reasons"],
                }
            )

        print("\nAGGREGATED PATH SAMPLES")

        aggregated = result["aggregated_analogue_paths"]

        print("\nTarget return sample:")
        pprint(aggregated["target_return_from_baseline"][:12])

        print("\nSpread abs sample:")
        pprint(aggregated["spread_abs"][:12])

        analysis_id = save_analogue_comparison(
            conn,
            pending_event_id,
            top_k=top_k,
            min_event_day=min_event_day,
            max_event_day=max_event_day,
        )
        conn.commit()

        print(f"\nSaved analogue_comparison in analysis_outputs with id={analysis_id}")


if __name__ == "__main__":
    main()