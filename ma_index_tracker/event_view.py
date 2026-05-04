from __future__ import annotations

import json
from typing import Any

from ma_index_tracker.db.database import save_analysis_output


def get_event_summary(conn, event_id: int) -> dict[str, Any]:
    query = """
    SELECT
        e.id AS event_id,
        e.bbg_deal_id,
        e.announcement_date,
        e.expected_completion_date,
        e.effective_date,
        e.index_implementation_date,
        e.deal_type,
        e.payment_type,
        e.offer_price,
        e.offer_currency,
        e.cash_terms_per_tgt_sh,
        e.stock_terms_acq_sh_per_tgt_sh,
        e.nature_of_bid,
        e.percent_owned_sought,
        e.status,
        e.notes,
        target.ticker AS target_ticker,
        target.name AS target_name,
        target.sector AS target_sector,
        acquirer.ticker AS acquirer_ticker,
        acquirer.name AS acquirer_name,
        acquirer.sector AS acquirer_sector
    FROM mna_events e
    JOIN companies target
        ON e.target_company_id = target.id
    LEFT JOIN companies acquirer
        ON e.acquirer_company_id = acquirer.id
    WHERE e.id = ?
    """
    row = conn.execute(query, (event_id,)).fetchone()
    if row is None:
        raise ValueError(f"No event found for event_id={event_id}")
    return dict(row)


def get_latest_analysis_output(conn, event_id: int, analysis_type: str) -> dict[str, Any] | None:
    query = """
    SELECT output_json
    FROM analysis_outputs
    WHERE event_id = ? AND analysis_type = ?
    ORDER BY id DESC
    LIMIT 1
    """
    row = conn.execute(query, (event_id, analysis_type)).fetchone()
    if row is None:
        return None
    return json.loads(row["output_json"])


def build_event_view(conn, event_id: int) -> dict[str, Any]:
    event_summary = get_event_summary(conn, event_id)
    target_analysis = get_latest_analysis_output(conn, event_id, "target_analysis")
    spread_analysis = get_latest_analysis_output(conn, event_id, "spread_analysis")

    if target_analysis is None:
        raise ValueError(f"No target_analysis found for event_id={event_id}")

    if spread_analysis is None:
        raise ValueError(f"No spread_analysis found for event_id={event_id}")

    result = {
        "event_id": event_id,
        "event_summary": event_summary,
        "headline_metrics": {
            "announcement_jump": target_analysis.get("announcement_jump"),
            "avg_pre_announcement_volume": target_analysis.get("avg_pre_announcement_volume"),
            "announcement_day_spread_abs": spread_analysis.get("announcement_day_spread_abs"),
            "announcement_day_spread_pct": spread_analysis.get("announcement_day_spread_pct"),
            "latest_spread_abs": spread_analysis.get("latest_spread_abs"),
            "latest_spread_pct": spread_analysis.get("latest_spread_pct"),
        },
        "target_analysis": target_analysis,
        "spread_analysis": spread_analysis,
    }

    return result


def save_event_view(conn, event_id: int) -> int:
    result = build_event_view(conn, event_id)
    analysis_id = save_analysis_output(
        conn=conn,
        event_id=event_id,
        analysis_type="event_view",
        output=result,
    )
    return analysis_id