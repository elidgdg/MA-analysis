from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ma_index_tracker.db.database import save_analysis_output


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_event_record(conn, event_id: int) -> dict[str, Any]:
    """
    Fetch one M&A event with target metadata.
    """
    query = """
    SELECT
        e.id AS event_id,
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
        target.id AS target_company_id,
        target.ticker AS target_ticker,
        target.name AS target_name
    FROM mna_events e
    JOIN companies target
        ON e.target_company_id = target.id
    WHERE e.id = ?
    """
    row = conn.execute(query, (event_id,)).fetchone()
    if row is None:
        raise ValueError(f"No event found for event_id={event_id}")
    return dict(row)


def get_target_market_series(conn, event_id: int) -> list[dict[str, Any]]:
    """
    Return target price + volume rows ordered by date.
    """
    query = """
    SELECT
        p.price_date AS date,
        p.open,
        p.high,
        p.low,
        p.close,
        p.adjusted_close,
        p.currency,
        v.volume
    FROM mna_events e
    JOIN prices p
        ON p.company_id = e.target_company_id
    LEFT JOIN volumes v
        ON v.company_id = e.target_company_id
       AND v.volume_date = p.price_date
    WHERE e.id = ?
    ORDER BY p.price_date
    """
    rows = conn.execute(query, (event_id,)).fetchall()
    return [dict(r) for r in rows]


def compute_target_analysis(conn, event_id: int) -> dict[str, Any]:
    """
    Compute target-side event analysis for one deal.

    Metrics:
    - baseline price = last trading day before announcement
    - announcement-day jump = first trading day on/after announcement vs baseline
    - return path from baseline
    - average pre-announcement volume over the 5 trading days before announcement
    - volume ratio path = daily volume / avg pre-announcement volume
    """
    event = get_event_record(conn, event_id)
    rows = get_target_market_series(conn, event_id)

    if not event["announcement_date"]:
        raise ValueError(f"Event {event_id} has no announcement_date")

    announcement_date = _parse_date(event["announcement_date"])

    pre_rows = [r for r in rows if _parse_date(r["date"]) < announcement_date]
    on_or_after_rows = [r for r in rows if _parse_date(r["date"]) >= announcement_date]

    if not pre_rows:
        raise ValueError(f"No pre-announcement market data for event {event_id}")

    if not on_or_after_rows:
        raise ValueError(f"No on/after-announcement market data for event {event_id}")

    baseline_row = pre_rows[-1]
    baseline_price = baseline_row["close"]
    if baseline_price is None:
        raise ValueError(f"Missing baseline close price for event {event_id}")

    announcement_row = on_or_after_rows[0]
    announcement_price = announcement_row["close"]
    if announcement_price is None:
        raise ValueError(f"Missing announcement close price for event {event_id}")

    announcement_jump = (announcement_price - baseline_price) / baseline_price

    pre_5 = pre_rows[-5:]
    pre_volumes = [r["volume"] for r in pre_5 if r["volume"] is not None]
    avg_pre_volume = None
    if pre_volumes:
        avg_pre_volume = sum(pre_volumes) / len(pre_volumes)

    event_day_map: dict[str, int] = {}

    n_pre = len(pre_rows)
    for i, row in enumerate(pre_rows):
        event_day_map[row["date"]] = i - n_pre  # ..., -3, -2, -1

    for i, row in enumerate(on_or_after_rows):
        event_day_map[row["date"]] = i  # 0, 1, 2, ...

    analysed_rows: list[dict[str, Any]] = []

    for r in rows:
        close_price = r["close"]
        volume = r["volume"]

        return_from_baseline = None
        if close_price is not None:
            return_from_baseline = (close_price - baseline_price) / baseline_price

        volume_ratio = None
        if volume is not None and avg_pre_volume not in (None, 0):
            volume_ratio = volume / avg_pre_volume

        analysed_rows.append(
            {
                "date": r["date"],
                "event_day": event_day_map[r["date"]],
                "close": close_price,
                "volume": volume,
                "return_from_baseline": return_from_baseline,
                "volume_ratio": volume_ratio,
            }
        )

    result = {
        "event_id": event_id,
        "target_ticker": event["target_ticker"],
        "target_name": event["target_name"],
        "announcement_date": event["announcement_date"],
        "baseline_date": baseline_row["date"],
        "baseline_price": baseline_price,
        "announcement_trading_date": announcement_row["date"],
        "announcement_day_price": announcement_price,
        "announcement_jump": announcement_jump,
        "avg_pre_announcement_volume": avg_pre_volume,
        "rows": analysed_rows,
    }

    return result


def save_target_analysis(conn, event_id: int) -> int:
    result = compute_target_analysis(conn, event_id)
    analysis_id = save_analysis_output(
        conn=conn,
        event_id=event_id,
        analysis_type="target_analysis",
        output=result,
    )
    return analysis_id