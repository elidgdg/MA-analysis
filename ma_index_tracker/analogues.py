from __future__ import annotations

import json
import math
from typing import Any

from ma_index_tracker.data_quality import classify_completed_event_quality, normalise_payment_type
from ma_index_tracker.db.database import save_analysis_output


def _safe_float(value: Any) -> float | None:
    if value in (None, "", "--"):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _extract_announced_total_value_mil(raw_deal_json: str | None) -> float | None:
    if not raw_deal_json:
        return None

    try:
        payload = json.loads(raw_deal_json)
    except Exception:
        return None

    action_terms = payload.get("action_terms", {})
    if "CA060" in action_terms:
        return _safe_float(action_terms.get("CA060"))

    selected_bulk_row = payload.get("selected_bulk_row", {})
    val = _safe_float(selected_bulk_row.get("Announced Total Value"))
    if val is None:
        return None

    if val > 1_000_000:
        return val / 1_000_000.0
    return val


def _extract_transaction_type(raw_deal_json: str | None) -> str | None:
    if not raw_deal_json:
        return None
    try:
        payload = json.loads(raw_deal_json)
    except Exception:
        return None
    action_terms = payload.get("action_terms", {})
    return action_terms.get("CA834")


def _payment_compatible(pending_pt: str | None, candidate_pt: str | None) -> bool:
    if pending_pt in (None, "undisclosed", "ambiguous"):
        return False
    if candidate_pt in (None, "undisclosed", "ambiguous"):
        return False
    return pending_pt == candidate_pt


def _size_similarity(v1: float | None, v2: float | None) -> float:
    if v1 is None or v2 is None or v1 <= 0 or v2 <= 0:
        return 0.0
    dist = abs(math.log(v1) - math.log(v2))
    return 1.0 / (1.0 + dist)


def _percent_sought_similarity(p1: float | None, p2: float | None) -> float:
    if p1 is None or p2 is None:
        return 0.0
    return max(0.0, 1.0 - abs(p1 - p2) / 100.0)


def _nature_match(n1: str | None, n2: str | None) -> float:
    if not n1 or not n2:
        return 0.0
    return 1.0 if n1.strip().lower() == n2.strip().lower() else 0.0


def _sector_match(s1: str | None, s2: str | None) -> float:
    if not s1 or not s2:
        return 0.0
    return 1.0 if s1.strip().lower() == s2.strip().lower() else 0.0


def _build_reason_list(
    pending: dict[str, Any],
    candidate: dict[str, Any],
    *,
    pending_payment_norm: str | None,
    candidate_payment_norm: str | None,
    size_similarity: float,
    same_sector: bool,
    tier: int,
) -> list[str]:
    reasons: list[str] = []

    if pending_payment_norm == candidate_payment_norm and pending_payment_norm is not None:
        reasons.append(f"same payment type ({candidate.get('payment_type')})")

    if same_sector:
        reasons.append(f"same target sector ({candidate.get('target_sector')})")
    elif tier == 2:
        reasons.append("fallback out-of-sector analogue")

    if size_similarity >= 0.80:
        reasons.append("very similar deal size")
    elif size_similarity >= 0.55:
        reasons.append("similar deal size")

    p1 = pending.get("percent_owned_sought")
    p2 = candidate.get("percent_owned_sought")
    if p1 is not None and p2 is not None and abs(p1 - p2) <= 5:
        reasons.append("similar percent sought")

    n1 = pending.get("nature_of_bid")
    n2 = candidate.get("nature_of_bid")
    if n1 and n2 and n1.strip().lower() == n2.strip().lower():
        reasons.append(f"same bid nature ({n2})")

    return reasons


def get_event_feature_row(conn, event_id: int) -> dict[str, Any]:
    query = """
    SELECT
        e.id AS event_id,
        e.bbg_deal_id,
        e.announcement_date,
        e.expected_completion_date,
        e.deal_type,
        e.payment_type,
        e.offer_currency,
        e.cash_terms_per_tgt_sh,
        e.stock_terms_acq_sh_per_tgt_sh,
        e.nature_of_bid,
        e.percent_owned_sought,
        e.status,
        e.raw_deal_json,
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

    result = dict(row)
    result["announced_total_value_mil"] = _extract_announced_total_value_mil(result.get("raw_deal_json"))
    result["transaction_type"] = _extract_transaction_type(result.get("raw_deal_json"))
    result["payment_type_normalized"] = normalise_payment_type(result.get("payment_type"))
    return result


def get_completed_candidate_rows(conn) -> list[dict[str, Any]]:
    query = """
    SELECT
        e.id AS event_id,
        e.bbg_deal_id,
        e.announcement_date,
        e.expected_completion_date,
        e.deal_type,
        e.payment_type,
        e.offer_currency,
        e.cash_terms_per_tgt_sh,
        e.stock_terms_acq_sh_per_tgt_sh,
        e.nature_of_bid,
        e.percent_owned_sought,
        e.status,
        e.raw_deal_json,
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
    WHERE e.status = 'Completed'
    """
    rows = conn.execute(query).fetchall()

    result = []
    for row in rows:
        d = dict(row)
        d["announced_total_value_mil"] = _extract_announced_total_value_mil(d.get("raw_deal_json"))
        d["transaction_type"] = _extract_transaction_type(d.get("raw_deal_json"))
        d["payment_type_normalized"] = normalise_payment_type(d.get("payment_type"))
        d["quality"] = classify_completed_event_quality(d)
        result.append(d)

    return result


def _within_tier_score(pending: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, dict[str, float]]:
    size_sim = _size_similarity(
        pending.get("announced_total_value_mil"),
        candidate.get("announced_total_value_mil"),
    )
    pct_sought_sim = _percent_sought_similarity(
        pending.get("percent_owned_sought"),
        candidate.get("percent_owned_sought"),
    )
    nature_sim = _nature_match(
        pending.get("nature_of_bid"),
        candidate.get("nature_of_bid"),
    )

    # Within a tier, size dominates, then percent sought, then bid nature
    score = (
        70.0 * size_sim
        + 20.0 * pct_sought_sim
        + 10.0 * nature_sim
    )

    return score, {
        "size": size_sim,
        "percent_sought": pct_sought_sim,
        "nature_of_bid": nature_sim,
    }


def _build_candidate_output(
    pending: dict[str, Any],
    candidate: dict[str, Any],
    *,
    pending_payment_norm: str | None,
    candidate_payment_norm: str | None,
    tier: int,
) -> dict[str, Any]:
    same_sector = _sector_match(
        pending.get("target_sector"),
        candidate.get("target_sector"),
    ) == 1.0

    within_tier_score, component_scores = _within_tier_score(pending, candidate)

    # Big fixed bonus for same-sector tier so all same-sector analogues rank ahead of out-of-sector ones.
    if tier == 1:
        total_score = 1000.0 + within_tier_score
    else:
        total_score = within_tier_score

    reasons = _build_reason_list(
        pending,
        candidate,
        pending_payment_norm=pending_payment_norm,
        candidate_payment_norm=candidate_payment_norm,
        size_similarity=component_scores["size"],
        same_sector=same_sector,
        tier=tier,
    )

    return {
        "event_id": candidate["event_id"],
        "bbg_deal_id": candidate["bbg_deal_id"],
        "target_name": candidate["target_name"],
        "target_ticker": candidate["target_ticker"],
        "acquirer_name": candidate["acquirer_name"],
        "acquirer_ticker": candidate["acquirer_ticker"],
        "announcement_date": candidate["announcement_date"],
        "expected_completion_date": candidate["expected_completion_date"],
        "payment_type": candidate["payment_type"],
        "payment_type_normalized": candidate_payment_norm,
        "target_sector": candidate["target_sector"],
        "nature_of_bid": candidate["nature_of_bid"],
        "percent_owned_sought": candidate["percent_owned_sought"],
        "announced_total_value_mil": candidate["announced_total_value_mil"],
        "tier": tier,
        "score": total_score,
        "component_scores": component_scores,
        "reasons": reasons,
    }


def compute_analogue_selection(conn, pending_event_id: int, top_k: int = 10) -> dict[str, Any]:
    pending = get_event_feature_row(conn, pending_event_id)

    if pending.get("status") != "Pending":
        raise ValueError(f"Event {pending_event_id} is not Pending")

    pending_payment_norm = pending.get("payment_type_normalized")
    if pending_payment_norm in (None, "undisclosed", "ambiguous"):
        raise ValueError(
            f"Pending event {pending_event_id} has unsuitable payment type for analogue selection: "
            f"{pending.get('payment_type')}"
        )

    candidates = get_completed_candidate_rows(conn)

    tier_1_candidates: list[dict[str, Any]] = []
    tier_2_candidates: list[dict[str, Any]] = []

    for c in candidates:
        candidate_payment_norm = c.get("payment_type_normalized")

        if not _payment_compatible(pending_payment_norm, candidate_payment_norm):
            continue

        if not c.get("quality", {}).get("is_clean", False):
            continue

        same_sector = _sector_match(
            pending.get("target_sector"),
            c.get("target_sector"),
        ) == 1.0

        out = _build_candidate_output(
            pending,
            c,
            pending_payment_norm=pending_payment_norm,
            candidate_payment_norm=candidate_payment_norm,
            tier=1 if same_sector else 2,
        )

        if same_sector:
            tier_1_candidates.append(out)
        else:
            tier_2_candidates.append(out)

    tier_1_candidates.sort(key=lambda x: x["score"], reverse=True)
    tier_2_candidates.sort(key=lambda x: x["score"], reverse=True)

    combined = tier_1_candidates + tier_2_candidates
    top_analogues = combined[:top_k]

    result = {
        "pending_event": {
            "event_id": pending["event_id"],
            "bbg_deal_id": pending["bbg_deal_id"],
            "target_name": pending["target_name"],
            "target_ticker": pending["target_ticker"],
            "acquirer_name": pending["acquirer_name"],
            "acquirer_ticker": pending["acquirer_ticker"],
            "announcement_date": pending["announcement_date"],
            "expected_completion_date": pending["expected_completion_date"],
            "payment_type": pending["payment_type"],
            "payment_type_normalized": pending_payment_norm,
            "target_sector": pending["target_sector"],
            "nature_of_bid": pending["nature_of_bid"],
            "percent_owned_sought": pending["percent_owned_sought"],
            "announced_total_value_mil": pending["announced_total_value_mil"],
        },
        "top_k": top_k,
        "candidate_pool_count": len(combined),
        "tier_1_same_sector_count": len(tier_1_candidates),
        "tier_2_fallback_count": len(tier_2_candidates),
        "analogues": top_analogues,
    }

    return result


def save_analogue_selection(conn, pending_event_id: int, top_k: int = 10) -> int:
    result = compute_analogue_selection(conn, pending_event_id, top_k=top_k)
    analysis_id = save_analysis_output(
        conn=conn,
        event_id=pending_event_id,
        analysis_type="analogue_selection",
        output=result,
    )
    return analysis_id