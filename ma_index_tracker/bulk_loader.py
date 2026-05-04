from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from ma_index_tracker.bloomberg_client import BloombergClient
from ma_index_tracker.db.database import (
    connect,
    insert_ma_event,
    upsert_company,
    upsert_price_rows,
    upsert_volume_rows,
)


@dataclass
class DealInputRow:
    source_file: str
    csv_row_index: int
    deal_type: str
    announce_date: str
    target_name: str
    acquirer_name: str
    seller_name: str | None
    announced_total_value_mil: float | None
    payment_type: str | None
    tv_ebitda: str | None
    deal_status: str | None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    if text in {"", "--", "nan", "NaN"}:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _to_iso_date_from_csv(value: str) -> str:
    dt = datetime.strptime(value, "%Y/%m/%d").date()
    return dt.isoformat()


def _default_start_date(announcement_date_iso: str) -> str:
    dt = datetime.strptime(announcement_date_iso, "%Y-%m-%d").date()
    return (dt - timedelta(days=10)).isoformat()


def _normalise_name(value: str) -> str:
    text = value.lower().strip()
    text = text.replace(",", " ")
    text = text.replace("/", " ")
    text = text.replace("&", " and ")
    text = re.sub(r"\bincorporated\b", "inc", text)
    text = re.sub(r"\bcorporation\b", "corp", text)
    text = re.sub(r"\bcompany\b", "co", text)
    text = re.sub(r"\blimited\b", "ltd", text)
    text = re.sub(r"\bholdings?\b", " ", text)
    text = re.sub(r"\bgroup\b", " ", text)
    text = re.sub(r"\bthe\b", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strings_similar(a: str, b: str) -> bool:
    na = _normalise_name(a)
    nb = _normalise_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return na in nb or nb in na


def _extract_first_number(text: str | None) -> float | None:
    if text in (None, "", "--"):
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(text))
    if not match:
        return None
    return float(match.group(0))


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


def read_deal_csv(csv_path: Path) -> list[DealInputRow]:
    df = pd.read_csv(csv_path)

    rows: list[DealInputRow] = []
    for idx, r in df.iterrows():
        rows.append(
            DealInputRow(
                source_file=csv_path.name,
                csv_row_index=int(idx),
                deal_type=str(r["Deal Type"]).strip(),
                announce_date=str(r["Announce Date"]).strip(),
                target_name=str(r["Target Name"]).strip(),
                acquirer_name=str(r["Acquirer Name"]).strip(),
                seller_name=None if pd.isna(r["Seller Name"]) else str(r["Seller Name"]).strip(),
                announced_total_value_mil=_safe_float(r["Announced Total Value (mil.)"]),
                payment_type=None if pd.isna(r["Payment Type"]) else str(r["Payment Type"]).strip(),
                tv_ebitda=None if pd.isna(r["TV/EBITDA"]) else str(r["TV/EBITDA"]).strip(),
                deal_status=None if pd.isna(r["Deal Status"]) else str(r["Deal Status"]).strip(),
            )
        )
    return rows


def _clean_company_name_for_lookup(name: str) -> str:
    text = name.strip()

    # remove anything after commas for lookup purposes
    if "," in text:
        text = text.split(",")[0].strip()

    # remove fund annotations in parentheses
    text = re.sub(r"\(.*?\)", " ", text)

    # common Bloomberg-style suffix cleanup
    replacements = [
        "/The",
        "/Old",
        "/CA",
        "/MA",
        "/Ireland",
        "/United States",
        "/US",
    ]
    for rep in replacements:
        text = text.replace(rep, "")

    text = text.replace("Corp/The", "Corp")
    text = text.replace("Co/The", "Co")
    text = text.replace("Group/The", "Group")
    text = text.replace("Inc/The", "Inc")

    text = re.sub(r"\s+", " ", text).strip()
    return text


def _name_query_variants(name: str) -> list[str]:
    cleaned = _clean_company_name_for_lookup(name)

    variants = [cleaned]

    shorter = cleaned
    suffixes = [
        " Inc",
        " Corp",
        " Co",
        " Ltd",
        " PLC",
        " LLC",
        " LP",
        " Holdings",
        " Group",
        " International",
        " Financial",
        " Pharmaceuticals",
        " Communications",
        " Technologies",
        " Systems",
        " Energy",
    ]
    for suf in suffixes:
        if shorter.endswith(suf):
            shorter = shorter[: -len(suf)].strip()
            variants.append(shorter)

    # de-duplicate preserving order
    out = []
    seen = set()
    for v in variants:
        if v and v not in seen:
            out.append(v)
            seen.add(v)
    return out


def _score_lookup_candidate(input_name: str, candidate: dict[str, Any]) -> int:
  score = 0

  sec = candidate.get("refdata_security") or candidate.get("security") or ""
  desc = candidate.get("description") or ""
  ticker = candidate.get("ticker") or ""
  yellow = candidate.get("yellowKey") or ""

  if "Equity" in sec:
      score += 10
  if " US Equity" in sec:
      score += 10

  if yellow.lower() == "equity":
      score += 6

  if _strings_similar(input_name, desc):
      score += 12
  if _strings_similar(input_name, sec):
      score += 8
  if input_name.lower() in desc.lower():
      score += 5

  if ticker:
      score += 1

  return score


def resolve_company_to_ticker(
    client: BloombergClient,
    company_name: str,
    *,
    max_results: int = 20,
    overrides: dict[str, str] | None = None,
) -> str:
    overrides = overrides or {}
    if company_name in overrides:
        return overrides[company_name]

    query_variants = _name_query_variants(company_name)

    all_candidates: list[dict[str, Any]] = []

    for query in query_variants:
        try:
            # no yellow-key filter here: let Bloomberg return candidates,
            # then we score them ourselves
            candidates = client.security_lookup(
                query,
                max_results=max_results,
                yellow_key_filter=None,
            )
            all_candidates.extend(candidates)
        except Exception:
            continue

    if not all_candidates:
        raise ValueError(f"No security lookup results for company '{company_name}'")

    # de-duplicate by security string
    unique: dict[str, dict[str, Any]] = {}
    for c in all_candidates:
        key = c.get("security") or repr(c)
        if key not in unique:
            unique[key] = c

    scored = []
    for c in unique.values():
        score = _score_lookup_candidate(company_name, c)
        if score > 0:
            scored.append((score, c))

    if not scored:
        raise ValueError(f"Could not resolve a usable equity ticker for '{company_name}'")

    scored.sort(key=lambda x: x[0], reverse=True)
    best_candidate = scored[0][1]
    best_security = best_candidate.get("refdata_security") or best_candidate.get("security")

    if not best_security:
        raise ValueError(f"Could not resolve a usable equity ticker for '{company_name}'")

    return best_security


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


def score_bulk_row_match(csv_row: DealInputRow, bulk_row: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    csv_date = _to_iso_date_from_csv(csv_row.announce_date)
    bulk_date = bulk_row.get("Announcement Date")
    if bulk_date == csv_date:
        score += 12
        reasons.append("date")

    if csv_row.deal_status and bulk_row.get("Deal Status") == csv_row.deal_status:
        score += 8
        reasons.append("status")

    if csv_row.payment_type and bulk_row.get("Payment Type") == csv_row.payment_type:
        score += 6
        reasons.append("payment_type")

    if csv_row.deal_type and bulk_row.get("Deal Type") == csv_row.deal_type:
        score += 3
        reasons.append("deal_type")

    csv_val = csv_row.announced_total_value_mil
    bulk_val = _safe_float(bulk_row.get("Announced Total Value"))
    if csv_val is not None and bulk_val is not None:
        denom = max(abs(csv_val), 1.0)
        rel_err = abs(csv_val - bulk_val) / denom
        if rel_err < 0.001:
            score += 10
            reasons.append("value_exactish")
        elif rel_err < 0.02:
            score += 7
            reasons.append("value_close")
        elif rel_err < 0.10:
            score += 3
            reasons.append("value_rough")

    return score, reasons


def select_best_bulk_row(csv_row: DealInputRow, bulk_rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored: list[tuple[int, list[str], dict[str, Any]]] = []

    for row in bulk_rows:
        score, reasons = score_bulk_row_match(csv_row, row)
        if score > 0:
            scored.append((score, reasons, row))

    if not scored:
        raise ValueError(
            f"No matching bulk M&A rows found for target={csv_row.target_name}, "
            f"announce_date={csv_row.announce_date}"
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, _, best_row = scored[0]

    if len(scored) > 1 and scored[1][0] == best_score:
        raise ValueError(
            f"Ambiguous bulk-row match for target={csv_row.target_name}, announce_date={csv_row.announce_date}"
        )

    return best_row


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
    return client.reference_data(security=action_security, fields=fields)


def _primary_acquirer_name(acquirer_name: str) -> str:
    """
    For consortium / comma-separated buyers, take the first named buyer as a lookup attempt.
    """
    first = acquirer_name.split(",")[0].strip()
    first = re.sub(r"\(.*?\)", " ", first)
    first = re.sub(r"\s+", " ", first).strip()
    return first


def load_single_deal_row(
    conn,
    client: BloombergClient,
    csv_row: DealInputRow,
    *,
    ticker_overrides: dict[str, str] | None = None,
    market_end_date: str | None = None,
) -> int:
    ticker_overrides = ticker_overrides or {}

    # 1. Resolve target only first
    target_ticker = resolve_company_to_ticker(
        client,
        csv_row.target_name,
        overrides=ticker_overrides,
    )

    target_ref = client.reference_data(
        security=target_ticker,
        fields=["NAME", "COUNTRY_ISO", "INDUSTRY_SECTOR"],
    )

    # 2. Use target ticker to identify the correct deal row + action id
    bulk_rows = fetch_bulk_mna_rows(client, target_ticker)
    selected = select_best_bulk_row(csv_row, bulk_rows)

    action_id = str(selected.get("Action Id"))
    action_terms = fetch_action_deal_terms(client, action_id)

    payment_type = action_terms.get("CA071") or selected.get("Payment Type")
    deal_type = action_terms.get("CA062") or selected.get("Deal Type")
    status = action_terms.get("CA061") or csv_row.deal_status or selected.get("Deal Status")

    ann_date_iso = action_terms.get("CA057") or selected.get("Announcement Date")
    exp_date_iso = action_terms.get("CA835")
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
    payment_type_normalized = _normalise_payment_type(payment_type)
    if payment_type_normalized == "cash":
        offer_price = cash_terms_per_tgt_sh

    # 3. Resolve acquirer only if it is useful/possible
    acquirer_ticker = None
    acquirer_ref = None
    acquirer_company_id = None

    need_acquirer_market_data = payment_type_normalized in {"stock", "mixed"}

    if need_acquirer_market_data:
        primary_acquirer = _primary_acquirer_name(csv_row.acquirer_name)
        try:
            acquirer_ticker = resolve_company_to_ticker(
                client,
                primary_acquirer,
                overrides=ticker_overrides,
            )
            acquirer_ref = client.reference_data(
                security=acquirer_ticker,
                fields=["NAME", "COUNTRY_ISO", "INDUSTRY_SECTOR"],
            )
        except Exception:
            # keep going; event still gets loaded, but spread may later be unavailable
            acquirer_ticker = None
            acquirer_ref = None

    raw_payload = {
        "csv_row": csv_row.__dict__,
        "selected_bulk_row": selected,
        "action_terms": action_terms,
        "resolved_target_ticker": target_ticker,
        "resolved_acquirer_ticker": acquirer_ticker,
    }

    target_company_id = upsert_company(
        conn=conn,
        ticker=target_ticker,
        name=target_ref.get("NAME"),
        exchange=None,
        country=target_ref.get("COUNTRY_ISO"),
        sector=target_ref.get("INDUSTRY_SECTOR"),
    )

    if acquirer_ticker and acquirer_ref:
        acquirer_company_id = upsert_company(
            conn=conn,
            ticker=acquirer_ticker,
            name=acquirer_ref.get("NAME"),
            exchange=None,
            country=acquirer_ref.get("COUNTRY_ISO"),
            sector=acquirer_ref.get("INDUSTRY_SECTOR"),
        )

    event_id = insert_ma_event(
        conn=conn,
        bbg_deal_id=action_id,
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
        notes=f"Loaded from {csv_row.source_file} row {csv_row.csv_row_index}",
        raw_deal_json=json.dumps(raw_payload, indent=2, sort_keys=True),
    )

    start_date = _default_start_date(ann_date_iso)
    end_date = market_end_date or datetime.today().date().isoformat()

    # 4. Always load target market data
    target_hist = client.historical_data(
        security=target_ticker,
        fields=["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST", "PX_VOLUME"],
        start_date=start_date,
        end_date=end_date,
    )

    target_price_rows = []
    target_volume_rows = []
    for row in target_hist:
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

    # 5. Load acquirer market data only if we have a public acquirer ticker
    if acquirer_ticker and acquirer_company_id is not None:
        acquirer_hist = client.historical_data(
            security=acquirer_ticker,
            fields=["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST", "PX_VOLUME"],
            start_date=start_date,
            end_date=end_date,
        )

        acq_price_rows = []
        acq_volume_rows = []
        for row in acquirer_hist:
            acq_price_rows.append(
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
            acq_volume_rows.append(
                {
                    "date": row["date"],
                    "volume": row.get("PX_VOLUME"),
                }
            )

        upsert_price_rows(conn, acquirer_company_id, acq_price_rows)
        upsert_volume_rows(conn, acquirer_company_id, acq_volume_rows)

    return event_id


def load_many_deals(
    *,
    db_path: Path,
    csv_paths: list[Path],
    ticker_overrides: dict[str, str] | None = None,
    market_end_date: str | None = None,
) -> dict[str, Any]:
    client = BloombergClient()
    ticker_overrides = ticker_overrides or {}

    all_rows: list[DealInputRow] = []
    for path in csv_paths:
        all_rows.extend(read_deal_csv(path))

    loaded = []
    failed = []

    with connect(db_path) as conn:
        for row in all_rows:
            try:
                event_id = load_single_deal_row(
                    conn,
                    client,
                    row,
                    ticker_overrides=ticker_overrides,
                    market_end_date=market_end_date,
                )
                conn.commit()
                loaded.append(
                    {
                        "event_id": event_id,
                        "source_file": row.source_file,
                        "csv_row_index": row.csv_row_index,
                        "target_name": row.target_name,
                        "acquirer_name": row.acquirer_name,
                        "announce_date": row.announce_date,
                        "deal_status": row.deal_status,
                    }
                )
                print(
                    f"[OK] {row.source_file} row {row.csv_row_index}: "
                    f"{row.target_name} / {row.acquirer_name}"
                )
            except Exception as e:
                conn.rollback()
                failed.append(
                    {
                        "source_file": row.source_file,
                        "csv_row_index": row.csv_row_index,
                        "target_name": row.target_name,
                        "acquirer_name": row.acquirer_name,
                        "announce_date": row.announce_date,
                        "deal_status": row.deal_status,
                        "error": str(e),
                    }
                )
                print(
                    f"[FAIL] {row.source_file} row {row.csv_row_index}: "
                    f"{row.target_name} / {row.acquirer_name} -> {e}"
                )

    return {
        "total_rows": len(all_rows),
        "loaded_count": len(loaded),
        "failed_count": len(failed),
        "loaded": loaded,
        "failed": failed,
    }