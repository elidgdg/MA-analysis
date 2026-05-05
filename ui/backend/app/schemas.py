from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PendingDealItem(BaseModel):
    event_id: int
    target_name: str
    acquirer_name: str | None
    announcement_date: str | None
    expected_completion_date: str | None
    payment_type: str | None
    target_sector: str | None


class DealSummaryResponse(BaseModel):
    event_id: int
    bbg_deal_id: str | None
    target_name: str
    target_ticker: str | None
    acquirer_name: str | None
    acquirer_ticker: str | None
    announcement_date: str | None
    expected_completion_date: str | None
    payment_type: str | None
    target_sector: str | None
    nature_of_bid: str | None
    percent_owned_sought: float | None
    announced_total_value_mil: float | None


class AnalogueSelectionResponse(BaseModel):
    data: dict[str, Any]


class AnalogueComparisonResponse(BaseModel):
    data: dict[str, Any]