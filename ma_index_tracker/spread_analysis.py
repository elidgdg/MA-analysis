from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ma_index_tracker.db.database import save_analysis_output


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _normalise_payment_type(payment_type: str | None) -> str | None:
    if payment_type in (None, "", "--"):
        return None
    pt = payment_type.strip().lower()
    if "cash" in pt and "stock" in pt:
        return "mixed"
    if "stock" in pt:
        return "stock"
    if "cash" in pt:
        return "cash"
    return pt


def get_event_with_terms(conn, event_id: int) -> dict[str, Any]:
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
        target.id AS target_company_id,
        target.ticker AS target_ticker,
        target.name AS target_name,
        acquirer.id AS acquirer_company_id,
        acquirer.ticker AS acquirer_ticker,
        acquirer.name AS acquirer_name
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


def get_price_series_for_company(conn, company_id: int) -> list[dict[str, Any]]:
    query = """
    SELECT
        price_date AS date,
        close
    FROM prices
    WHERE company_id = ?
    ORDER BY price_date
    """
    rows = conn.execute(query, (company_id,)).fetchall()
    return [dict(r) for r in rows]


def _build_event_day_map(target_rows: list[dict[str, Any]], announcement_date: str) -> dict[str, int]:
    ann_date = _parse_date(announcement_date)

    pre_rows = [r for r in target_rows if _parse_date(r["date"]) < ann_date]
    on_or_after_rows = [r for r in target_rows if _parse_date(r["date"]) >= ann_date]

    if not pre_rows:
        raise ValueError("No pre-announcement rows found.")
    if not on_or_after_rows:
        raise ValueError("No on/after-announcement rows found.")

    mapping: dict[str, int] = {}

    n_pre = len(pre_rows)
    for i, row in enumerate(pre_rows):
        mapping[row["date"]] = i - n_pre  # ..., -3, -2, -1

    for i, row in enumerate(on_or_after_rows):
        mapping[row["date"]] = i  # 0, 1, 2, ...

    return mapping


def compute_spread_analysis(conn, event_id: int) -> dict[str, Any]:
    event = get_event_with_terms(conn, event_id)

    if not event["announcement_date"]:
        raise ValueError(f"Event {event_id} has no announcement_date")

    target_rows = get_price_series_for_company(conn, event["target_company_id"])
    if not target_rows:
        raise ValueError(f"No target price rows found for event {event_id}")

    acquirer_rows_by_date: dict[str, dict[str, Any]] = {}
    if event["acquirer_company_id"] is not None:
        acquirer_rows = get_price_series_for_company(conn, event["acquirer_company_id"])
        acquirer_rows_by_date = {r["date"]: r for r in acquirer_rows}

    event_day_map = _build_event_day_map(target_rows, event["announcement_date"])
    payment_type_normalized = _normalise_payment_type(event["payment_type"])

    cash_terms = event["cash_terms_per_tgt_sh"]
    stock_terms = event["stock_terms_acq_sh_per_tgt_sh"]

    analysed_rows: list[dict[str, Any]] = []

    for target_row in target_rows:
        row_date = target_row["date"]
        event_day = event_day_map[row_date]
        target_close = target_row["close"]

        acquirer_close = None
        if row_date in acquirer_rows_by_date:
            acquirer_close = acquirer_rows_by_date[row_date]["close"]

        implied_deal_value = None
        spread_abs = None
        spread_pct = None

        # Only meaningful from announcement onward
        if event_day >= 0 and target_close is not None:
            if payment_type_normalized == "cash":
                implied_deal_value = cash_terms

            elif payment_type_normalized == "stock":
                if stock_terms is not None and acquirer_close is not None:
                    implied_deal_value = stock_terms * acquirer_close

            elif payment_type_normalized == "mixed":
                if cash_terms is not None and stock_terms is not None and acquirer_close is not None:
                    implied_deal_value = cash_terms + (stock_terms * acquirer_close)

            if implied_deal_value is not None:
                spread_abs = implied_deal_value - target_close
                if implied_deal_value != 0:
                    spread_pct = spread_abs / implied_deal_value

        analysed_rows.append(
            {
                "date": row_date,
                "event_day": event_day,
                "target_close": target_close,
                "acquirer_close": acquirer_close,
                "implied_deal_value": implied_deal_value,
                "spread_abs": spread_abs,
                "spread_pct": spread_pct,
            }
        )

    day_0 = next((r for r in analysed_rows if r["event_day"] == 0), None)
    day_5 = next((r for r in analysed_rows if r["event_day"] == 5), None)

    valid_rows = [r for r in analysed_rows if r["spread_abs"] is not None]
    latest_valid = valid_rows[-1] if valid_rows else None

    result = {
        "event_id": event_id,
        "bbg_deal_id": event["bbg_deal_id"],
        "target_ticker": event["target_ticker"],
        "target_name": event["target_name"],
        "acquirer_ticker": event["acquirer_ticker"],
        "acquirer_name": event["acquirer_name"],
        "announcement_date": event["announcement_date"],
        "payment_type": event["payment_type"],
        "deal_type_normalized": payment_type_normalized,
        "cash_terms_per_tgt_sh": cash_terms,
        "stock_terms_acq_sh_per_tgt_sh": stock_terms,
        "announcement_day_spread_abs": day_0["spread_abs"] if day_0 else None,
        "announcement_day_spread_pct": day_0["spread_pct"] if day_0 else None,
        "day_5_spread_abs": day_5["spread_abs"] if day_5 else None,
        "day_5_spread_pct": day_5["spread_pct"] if day_5 else None,
        "latest_spread_abs": latest_valid["spread_abs"] if latest_valid else None,
        "latest_spread_pct": latest_valid["spread_pct"] if latest_valid else None,
        "rows": analysed_rows,
    }

    return result


def save_spread_analysis(conn, event_id: int) -> int:
    result = compute_spread_analysis(conn, event_id)
    analysis_id = save_analysis_output(
        conn=conn,
        event_id=event_id,
        analysis_type="spread_analysis",
        output=result,
    )
    return analysis_id