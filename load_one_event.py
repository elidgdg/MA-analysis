from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ma_index_tracker.bloomberg_client import BloombergClient
from ma_index_tracker.db.database import (
    connect,
    insert_ma_event,
    upsert_company,
    upsert_price_rows,
    upsert_volume_rows,
)

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"


def _to_iso_date(value: str | None) -> str | None:
    if value in (None, "", "--"):
        return None
    return datetime.strptime(value, "%Y-%m-%d").date().isoformat()


def _default_start_date(announcement_date: str) -> str:
    dt = datetime.strptime(announcement_date, "%Y-%m-%d").date()
    return (dt - timedelta(days=10)).isoformat()


def _safe_float(value):
    if value in (None, "", "--"):
        return None
    try:
        return float(value)
    except Exception:
        return None


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


def _extract_first_number(text: str | None) -> float | None:
    if text in (None, "", "--"):
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def fetch_bulk_mna_rows(client: BloombergClient, target_ticker: str) -> list[dict[str, Any]]:
    data = client.reference_data(
        security=target_ticker,
        fields=["MERGERS_AND_ACQUISITIONS"],
    )
    rows = data.get("MERGERS_AND_ACQUISITIONS")
    if rows is None:
        raise ValueError(f"No MERGERS_AND_ACQUISITIONS data returned for {target_ticker}")
    if not isinstance(rows, list):
        raise ValueError(f"Expected bulk M&A rows to be a list, got {type(rows)}")
    return rows


def select_deal_row(
    rows: list[dict[str, Any]],
    *,
    announcement_date: str,
    deal_status: str | None = None,
    action_id: str | None = None,
) -> dict[str, Any]:
    if action_id is not None:
        for row in rows:
            if str(row.get("Action Id")) == str(action_id):
                return row

    candidates = [r for r in rows if r.get("Announcement Date") == announcement_date]

    if deal_status is not None:
        status_matches = [r for r in candidates if r.get("Deal Status") == deal_status]
        if len(status_matches) == 1:
            return status_matches[0]
        if len(status_matches) > 1:
            raise ValueError(f"Multiple rows matched date={announcement_date} and status={deal_status}")

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) == 0:
        raise ValueError(f"No deal row matched announcement date {announcement_date}")

    raise ValueError(
        f"Multiple deal rows matched announcement date {announcement_date}. "
        f"Pass action_id to disambiguate."
    )


def fetch_action_deal_terms(client: BloombergClient, action_id: str) -> dict[str, Any]:
    action_security = f"{action_id} Action"

    fields = [
        "CA061",  # Deal Status
        "CA062",  # Deal Type
        "CA075",  # Nature of Bid
        "CA834",  # Transaction Type
        "CA057",  # Announced Date
        "CA835",  # Expected Completion Date
        "CA932",  # Mergers Agreement Date
        "CA947",  # Drop Dead Date
        "CA848",  # Deal Currency
        "CA071",  # Payment Type
        "CA069",  # Cash Value
        "CA072",  # Cash Terms
        "CA073",  # Stock Terms
        "CA065",  # Percent Owned
        "CA066",  # Percent Sought
        "CA060",  # Announced Total Value
        "CA059",  # Current Total Value
        "CA063",  # Announced Premium
        "CA067",  # Current Premium
        "CA849",  # Gross Spread
        "CA_MA_DEAL_PROBABILITY_PERCENT",
    ]

    data = client.reference_data(
        security=action_security,
        fields=fields,
    )
    return data


def load_event_from_bloomberg(
    *,
    db_path: Path,
    target_ticker: str,
    acquirer_ticker: str | None,
    announcement_date: str,
    status_override: str | None = None,
    notes: str | None = None,
    action_id: str | None = None,
    market_end_date: str | None = None,
) -> int:
    client = BloombergClient()

    target_ref = client.reference_data(
        security=target_ticker,
        fields=["NAME", "COUNTRY_ISO", "INDUSTRY_SECTOR"],
    )

    acquirer_ref = None
    if acquirer_ticker:
        acquirer_ref = client.reference_data(
            security=acquirer_ticker,
            fields=["NAME", "COUNTRY_ISO", "INDUSTRY_SECTOR"],
        )

    bulk_rows = fetch_bulk_mna_rows(client, target_ticker)
    selected = select_deal_row(
        bulk_rows,
        announcement_date=announcement_date,
        deal_status=status_override,
        action_id=action_id,
    )

    bbg_deal_id = str(selected.get("Action Id"))
    action_terms = fetch_action_deal_terms(client, bbg_deal_id)

    payment_type = action_terms.get("CA071") or selected.get("Payment Type")
    deal_type = action_terms.get("CA062") or selected.get("Deal Type")
    status = action_terms.get("CA061") or status_override or selected.get("Deal Status")

    ann_date_iso = _to_iso_date(action_terms.get("CA057") or selected.get("Announcement Date"))
    exp_date_iso = _to_iso_date(action_terms.get("CA835"))
    eff_date_iso = None
    impl_date_iso = None

    offer_currency = action_terms.get("CA848") or selected.get("Currency")
    nature_of_bid = action_terms.get("CA075")
    percent_owned_sought = _safe_float(action_terms.get("CA066"))

    cash_terms_text = action_terms.get("CA072")
    stock_terms_text = action_terms.get("CA073")

    cash_terms_per_tgt_sh = _extract_first_number(cash_terms_text)
    stock_terms_acq_sh_per_tgt_sh = _extract_first_number(stock_terms_text)

    offer_price = None
    if _normalise_payment_type(payment_type) == "cash":
        offer_price = cash_terms_per_tgt_sh

    raw_payload = {
        "selected_bulk_row": selected,
        "action_terms": action_terms,
    }

    start_date = _default_start_date(announcement_date)
    end_date = _to_iso_date(market_end_date) if market_end_date else datetime.today().date().isoformat()

    with connect(db_path) as conn:
        target_company_id = upsert_company(
            conn=conn,
            ticker=target_ticker,
            name=target_ref.get("NAME"),
            exchange=None,
            country=target_ref.get("COUNTRY_ISO"),
            sector=target_ref.get("INDUSTRY_SECTOR"),
        )

        acquirer_company_id = None
        if acquirer_ticker:
            acquirer_company_id = upsert_company(
                conn=conn,
                ticker=acquirer_ticker,
                name=acquirer_ref.get("NAME") if acquirer_ref else None,
                exchange=None,
                country=acquirer_ref.get("COUNTRY_ISO") if acquirer_ref else None,
                sector=acquirer_ref.get("INDUSTRY_SECTOR") if acquirer_ref else None,
            )

        event_id = insert_ma_event(
            conn=conn,
            bbg_deal_id=bbg_deal_id,
            target_company_id=target_company_id,
            acquirer_company_id=acquirer_company_id,
            announcement_date=ann_date_iso,
            expected_completion_date=exp_date_iso,
            effective_date=eff_date_iso,
            index_implementation_date=impl_date_iso,
            deal_type=deal_type,
            payment_type=payment_type,
            offer_price=offer_price,
            offer_currency=offer_currency,
            cash_terms_per_tgt_sh=cash_terms_per_tgt_sh,
            stock_terms_acq_sh_per_tgt_sh=stock_terms_acq_sh_per_tgt_sh,
            nature_of_bid=nature_of_bid,
            percent_owned_sought=percent_owned_sought,
            status=status,
            notes=notes,
            raw_deal_json=json.dumps(raw_payload, indent=2, sort_keys=True),
        )

        target_rows = client.historical_data(
            security=target_ticker,
            fields=["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST", "PX_VOLUME"],
            start_date=start_date,
            end_date=end_date,
        )

        target_price_rows = []
        target_volume_rows = []

        for row in target_rows:
            target_price_rows.append(
                {
                    "date": row["date"],
                    "open": row.get("PX_OPEN"),
                    "high": row.get("PX_HIGH"),
                    "low": row.get("PX_LOW"),
                    "close": row.get("PX_LAST"),
                    "adjusted_close": row.get("PX_LAST"),
                    "currency": offer_currency or "USD",
                }
            )
            target_volume_rows.append(
                {
                    "date": row["date"],
                    "volume": row.get("PX_VOLUME"),
                }
            )

        upsert_price_rows(conn, target_company_id, target_price_rows)
        upsert_volume_rows(conn, target_company_id, target_volume_rows)

        if acquirer_ticker and acquirer_company_id is not None:
            acquirer_rows = client.historical_data(
                security=acquirer_ticker,
                fields=["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST", "PX_VOLUME"],
                start_date=start_date,
                end_date=end_date,
            )

            acquirer_price_rows = []
            acquirer_volume_rows = []

            for row in acquirer_rows:
                acquirer_price_rows.append(
                    {
                        "date": row["date"],
                        "open": row.get("PX_OPEN"),
                        "high": row.get("PX_HIGH"),
                        "low": row.get("PX_LOW"),
                        "close": row.get("PX_LAST"),
                        "adjusted_close": row.get("PX_LAST"),
                        "currency": offer_currency or "USD",
                    }
                )
                acquirer_volume_rows.append(
                    {
                        "date": row["date"],
                        "volume": row.get("PX_VOLUME"),
                    }
                )

            upsert_price_rows(conn, acquirer_company_id, acquirer_price_rows)
            upsert_volume_rows(conn, acquirer_company_id, acquirer_volume_rows)

        conn.commit()

    return event_id


def main() -> None:
    event_id = load_event_from_bloomberg(
        db_path=DB_PATH,
        target_ticker="NSC US Equity",
        acquirer_ticker="UNP US Equity",
        announcement_date="2025-07-29",
        status_override="Pending",
        notes="Pending Norfolk Southern / Union Pacific deal loaded from bulk M&A row + Action object",
        action_id="243270965",
    )
    print(f"Loaded event {event_id}")


if __name__ == "__main__":
    main()