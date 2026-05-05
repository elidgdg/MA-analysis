from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_db_path, get_project_root
from app.schemas import (
    AnalogueComparisonResponse,
    AnalogueSelectionResponse,
    DealSummaryResponse,
    EventSourcesResponse,
    PendingDealItem,
    SourceItem,
)

PROJECT_ROOT = get_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ma_index_tracker.analogues import compute_analogue_selection, get_event_feature_row
from ma_index_tracker.comparison import compute_analogue_comparison
from ma_index_tracker.db.database import connect, get_event_sources


app = FastAPI(title="M&A Analogue Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_csv_acquirer_name(raw_deal_json: str | None) -> str | None:
    if not raw_deal_json:
        return None
    try:
        payload = json.loads(raw_deal_json)
    except Exception:
        return None

    csv_row = payload.get("csv_row", {})
    name = csv_row.get("acquirer_name")
    if name in (None, "", "--"):
        return None
    return str(name).strip()


def with_acquirer_fallback(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)

    if out.get("acquirer_name") in (None, "", "--"):
        fallback_name = extract_csv_acquirer_name(out.get("raw_deal_json"))
        if fallback_name:
            out["acquirer_name"] = fallback_name

    return out


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/pending-deals", response_model=list[PendingDealItem])
def get_pending_deals() -> list[PendingDealItem]:
    db_path = get_db_path()

    query = """
    SELECT
        e.id AS event_id,
        target.name AS target_name,
        acquirer.name AS acquirer_name,
        e.raw_deal_json,
        e.announcement_date,
        e.expected_completion_date,
        e.payment_type,
        target.sector AS target_sector
    FROM mna_events e
    JOIN companies target
        ON e.target_company_id = target.id
    LEFT JOIN companies acquirer
        ON e.acquirer_company_id = acquirer.id
    WHERE e.status = 'Pending'
    ORDER BY e.announcement_date
    """

    with connect(db_path) as conn:
        rows = [with_acquirer_fallback(dict(r)) for r in conn.execute(query).fetchall()]

    return [
        PendingDealItem(
            event_id=row["event_id"],
            target_name=row["target_name"],
            acquirer_name=row.get("acquirer_name"),
            announcement_date=row.get("announcement_date"),
            expected_completion_date=row.get("expected_completion_date"),
            payment_type=row.get("payment_type"),
            target_sector=row.get("target_sector"),
        )
        for row in rows
    ]


@app.get("/deal/{event_id}/summary", response_model=DealSummaryResponse)
def get_deal_summary(event_id: int) -> DealSummaryResponse:
    db_path = get_db_path()

    with connect(db_path) as conn:
        try:
            row = get_event_feature_row(conn, event_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    row = with_acquirer_fallback(row)

    return DealSummaryResponse(
        event_id=row["event_id"],
        bbg_deal_id=row.get("bbg_deal_id"),
        target_name=row["target_name"],
        target_ticker=row.get("target_ticker"),
        acquirer_name=row.get("acquirer_name"),
        acquirer_ticker=row.get("acquirer_ticker"),
        announcement_date=row.get("announcement_date"),
        expected_completion_date=row.get("expected_completion_date"),
        payment_type=row.get("payment_type"),
        target_sector=row.get("target_sector"),
        nature_of_bid=row.get("nature_of_bid"),
        percent_owned_sought=row.get("percent_owned_sought"),
        announced_total_value_mil=row.get("announced_total_value_mil"),
    )


@app.get("/deal/{event_id}/sources", response_model=EventSourcesResponse)
def get_deal_sources(event_id: int) -> EventSourcesResponse:
    db_path = get_db_path()

    with connect(db_path) as conn:
        exists = conn.execute(
            "SELECT id FROM mna_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail=f"No event found for event_id={event_id}")

        sources = get_event_sources(conn, event_id)

    return EventSourcesResponse(
        event_id=event_id,
        sources=[SourceItem(**dict(source)) for source in sources],
    )


@app.get("/deal/{event_id}/analogues", response_model=AnalogueSelectionResponse)
def get_deal_analogues(event_id: int, top_k: int = 10) -> AnalogueSelectionResponse:
    db_path = get_db_path()

    with connect(db_path) as conn:
        try:
            result = compute_analogue_selection(conn, event_id, top_k=top_k)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    pending_event = with_acquirer_fallback(result["pending_event"])
    analogues = [with_acquirer_fallback(row) for row in result["analogues"]]

    result = dict(result)
    result["pending_event"] = pending_event
    result["analogues"] = analogues

    return AnalogueSelectionResponse(data=result)


@app.get("/deal/{event_id}/comparison", response_model=AnalogueComparisonResponse)
def get_deal_comparison(
    event_id: int,
    top_k: int = 10,
    min_event_day: int = -5,
    max_event_day: int = 60,
) -> AnalogueComparisonResponse:
    db_path = get_db_path()

    with connect(db_path) as conn:
        try:
            result = compute_analogue_comparison(
                conn,
                event_id,
                top_k=top_k,
                min_event_day=min_event_day,
                max_event_day=max_event_day,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    result = dict(result)
    result["analogue_selection"] = dict(result["analogue_selection"])
    result["analogue_selection"]["pending_event"] = with_acquirer_fallback(
        result["analogue_selection"]["pending_event"]
    )
    result["analogue_selection"]["analogues"] = [
        with_acquirer_fallback(row)
        for row in result["analogue_selection"]["analogues"]
    ]

    return AnalogueComparisonResponse(data=result)