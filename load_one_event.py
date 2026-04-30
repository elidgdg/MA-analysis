from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from ma_index_tracker.db.database import (
    connect,
    insert_ma_event,
    upsert_company,
    upsert_price_rows,
    upsert_volume_rows,
)
from ma_index_tracker.bloomberg_client import BloombergClient


DB_PATH = Path("ma_index_tracker.sqlite")


def _to_iso_date(value: str) -> str:
    """Convert YYYY-MM-DD input to ISO date string."""
    return datetime.strptime(value, "%Y-%m-%d").date().isoformat()


def _default_start_date(announcement_date: str) -> str:
    """
    Approximate start date as 10 calendar days before announcement.
    This is a simple proxy for '5 trading days before'.
    """
    dt = datetime.strptime(announcement_date, "%Y-%m-%d").date()
    return (dt - timedelta(days=10)).isoformat()


def load_event(
    *,
    db_path: Path,
    target_ticker: str,
    acquirer_ticker: str | None,
    announcement_date: str,
    effective_date: str | None,
    index_implementation_date: str | None,
    deal_type: str | None,
    offer_price: float | None,
    offer_currency: str | None,
    status: str | None,
    notes: str | None,
    target_name: str | None = None,
    acquirer_name: str | None = None,
    target_exchange: str | None = None,
    acquirer_exchange: str | None = None,
    target_country: str | None = None,
    acquirer_country: str | None = None,
    target_sector: str | None = None,
    acquirer_sector: str | None = None,
    market_end_date: str | None = None,
) -> int:
    """
    Insert one M&A event and load market data for target/acquirer.

    Parameters
    ----------
    announcement_date, effective_date, index_implementation_date, market_end_date
        Must be in YYYY-MM-DD format if provided.
    """
    ann_date_iso = _to_iso_date(announcement_date)
    eff_date_iso = _to_iso_date(effective_date) if effective_date else None
    impl_date_iso = _to_iso_date(index_implementation_date) if index_implementation_date else None

    start_date = _default_start_date(announcement_date)
    end_date = _to_iso_date(market_end_date) if market_end_date else datetime.today().date().isoformat()

    client = BloombergClient()

    with connect(db_path) as conn:
        # 1. Upsert companies
        target_company_id = upsert_company(
            conn=conn,
            ticker=target_ticker,
            name=target_name,
            exchange=target_exchange,
            country=target_country,
            sector=target_sector,
        )

        acquirer_company_id = None
        if acquirer_ticker:
            acquirer_company_id = upsert_company(
                conn=conn,
                ticker=acquirer_ticker,
                name=acquirer_name,
                exchange=acquirer_exchange,
                country=acquirer_country,
                sector=acquirer_sector,
            )

        # 2. Insert event row
        event_id = insert_ma_event(
            conn=conn,
            target_company_id=target_company_id,
            acquirer_company_id=acquirer_company_id,
            announcement_date=ann_date_iso,
            effective_date=eff_date_iso,
            index_implementation_date=impl_date_iso,
            deal_type=deal_type,
            offer_price=offer_price,
            offer_currency=offer_currency,
            status=status,
            notes=notes,
        )

        # 3. Load target market data
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
                    "currency": offer_currency,
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

        # 4. Load acquirer market data if present
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
                        "currency": offer_currency,
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
    """
    Example: one pending deal.
    Replace these values with your real deal.
    """
    event_id = load_event(
        db_path=DB_PATH,
        target_ticker="NSC US Equity",
        acquirer_ticker="UNP US Equity",
        announcement_date="2025-07-29",
        effective_date=None,
        index_implementation_date=None,
        deal_type="stock",
        offer_price=None,
        offer_currency="USD",
        status="Pending",
        notes="Pending Norfolk Southern / Union Pacific deal",
        target_name="Norfolk Southern Corp",
        acquirer_name="Union Pacific Corp",
        target_exchange="NYSE",
        acquirer_exchange="NYSE",
        target_country="USA",
        acquirer_country="USA",
        target_sector="Industrials",
        acquirer_sector="Industrials",
    )
    print(f"Loaded event {event_id}")


if __name__ == "__main__":
    main()