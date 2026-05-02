from __future__ import annotations

import json
import re
from typing import Any


_BAD_NAME_PATTERNS = [
    r"\bCDS\b",
    r"\bSR\s+\d+Y\b",
    r"\bD\d+\b",
    r"\bINDEX\b",
    r"\bCURNCY\b",
    r"\bCOMDTY\b",
    r"\bGOVT\b",
]


def looks_like_bad_company_name(name: str | None) -> bool:
    if not name:
        return True

    text = name.strip().upper()

    for pat in _BAD_NAME_PATTERNS:
        if re.search(pat, text):
            return True

    if len(text) < 3:
        return True

    return False


def looks_like_equity_ticker(ticker: str | None) -> bool:
    if not ticker:
        return False
    return ticker.strip().upper().endswith(" EQUITY")


def extract_action_terms(raw_deal_json: str | None) -> dict[str, Any]:
    if not raw_deal_json:
        return {}
    try:
        payload = json.loads(raw_deal_json)
    except Exception:
        return {}
    return payload.get("action_terms", {}) or {}


def extract_announced_total_value_mil(raw_deal_json: str | None) -> float | None:
    action_terms = extract_action_terms(raw_deal_json)
    value = action_terms.get("CA060")
    if value in (None, "", "--"):
        return None
    try:
        return float(value)
    except Exception:
        return None


def normalise_payment_type(payment_type: str | None) -> str | None:
    if payment_type in (None, "", "--"):
        return None
    pt = payment_type.strip().lower()
    if "cash and stock" in pt:
        return "mixed"
    if "cash or stock" in pt:
        return "ambiguous"
    if "stock" in pt:
        return "stock"
    if "cash" in pt:
        return "cash"
    if "undisclosed" in pt:
        return "undisclosed"
    return pt


def classify_completed_event_quality(row: dict[str, Any]) -> dict[str, Any]:
    """
    Quality assessment specifically for analogue selection.

    Rules:
    - target side must always be sane
    - payment type must be usable
    - announced total value must be present
    - for stock/mixed deals, acquirer side must also be sane enough
    """
    issues: list[str] = []

    target_name = row.get("target_name")
    target_ticker = row.get("target_ticker")
    acquirer_name = row.get("acquirer_name")
    acquirer_ticker = row.get("acquirer_ticker")
    payment_type = row.get("payment_type")
    target_sector = row.get("target_sector")
    raw_deal_json = row.get("raw_deal_json")

    announced_total_value_mil = extract_announced_total_value_mil(raw_deal_json)
    payment_norm = normalise_payment_type(payment_type)

    if looks_like_bad_company_name(target_name):
        issues.append("bad_target_name")

    if not looks_like_equity_ticker(target_ticker):
        issues.append("bad_target_ticker")

    if payment_norm in (None, "undisclosed", "ambiguous"):
        issues.append("bad_payment_type")

    if not target_sector:
        issues.append("missing_target_sector")

    if announced_total_value_mil is None or announced_total_value_mil <= 0:
        issues.append("missing_announced_total_value")

    # For stock / mixed deals, we do care about the acquirer side being sane.
    if payment_norm in {"stock", "mixed"}:
        acquirer_name_bad = looks_like_bad_company_name(acquirer_name)
        acquirer_ticker_bad = acquirer_ticker is not None and not looks_like_equity_ticker(acquirer_ticker)

        if acquirer_name_bad:
            issues.append("bad_acquirer_name_for_stock_or_mixed")

        if acquirer_ticker_bad:
            issues.append("bad_acquirer_ticker_for_stock_or_mixed")

    return {
        "is_clean": len(issues) == 0,
        "issues": issues,
        "announced_total_value_mil": announced_total_value_mil,
        "payment_type_normalized": payment_norm,
    }