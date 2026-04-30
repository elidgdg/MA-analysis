"""Typed records passed between layers."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class CompanyRecord:
    """Represents a company record."""
    ticker: str
    name: str | None = None
    exchange: str | None = None
    country: str | None = None
    sector: str | None = None

@dataclass(frozen=True)
class DealRecord:
    """Represents a M&A event record."""
    target_ticker: str
    acquirer_ticker: str | None
    announcement_date: str | None
    effective_date: str | None
    index_implementation_date: str | None
    deal_type: str | None
    offer_price: float | None
    offer_currency: str | None
    status: str | None
    notes: str | None

@dataclass(frozen=True)
class OwnershipRecord:
    """Shareholder position for a company at a given date."""
    shareholder_name: str
    holder_type: str | None
    country: str | None
    snapshot_date: str
    rank: int | None
    shares_held: float | None
    ownership_pct: float | None
    source: str | None

@dataclass(frozen=True)
class PriceVolumeRecord:
    """Represents a price/volume record for a company on a given date."""
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adjusted_close: float | None
    currency: str | None
    volume: float | None
