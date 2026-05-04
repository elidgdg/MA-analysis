from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .schema import SCHEMA_SQL


def connect(db_path: Path | str) -> sqlite3.Connection:
    """
    Connect to the SQLite database and return a row-dict style connection.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path | str) -> None:
    """
    Initialize the database schema.
    """
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)


def upsert_company(
    conn: sqlite3.Connection,
    ticker: str,
    name: str | None = None,
    exchange: str | None = None,
    country: str | None = None,
    sector: str | None = None,
) -> int:
    """
    Insert/update a company and return its ID.
    """
    conn.execute(
        """
        INSERT INTO companies (ticker, name, exchange, country, sector)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            name = COALESCE(excluded.name, companies.name),
            exchange = COALESCE(excluded.exchange, companies.exchange),
            country = COALESCE(excluded.country, companies.country),
            sector = COALESCE(excluded.sector, companies.sector)
        """,
        (ticker, name, exchange, country, sector),
    )

    row = conn.execute(
        "SELECT id FROM companies WHERE ticker = ?",
        (ticker,),
    ).fetchone()

    return int(row["id"])


def upsert_shareholder(
    conn: sqlite3.Connection,
    name: str,
    holder_type: str | None = None,
    country: str | None = None,
) -> int:
    """
    Insert/update a shareholder and return its ID.
    """
    conn.execute(
        """
        INSERT INTO shareholders (name, holder_type, country)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            holder_type = COALESCE(excluded.holder_type, shareholders.holder_type),
            country = COALESCE(excluded.country, shareholders.country)
        """,
        (name, holder_type, country),
    )

    row = conn.execute(
        "SELECT id FROM shareholders WHERE name = ?",
        (name,),
    ).fetchone()

    return int(row["id"])


def insert_ma_event(
    conn: sqlite3.Connection,
    *,
    bbg_deal_id: str | None,
    target_company_id: int,
    acquirer_company_id: int | None,
    announcement_date: str | None,
    expected_completion_date: str | None,
    effective_date: str | None,
    index_implementation_date: str | None,
    deal_type: str | None,
    payment_type: str | None,
    offer_price: float | None,
    offer_currency: str | None,
    cash_terms_per_tgt_sh: float | None,
    stock_terms_acq_sh_per_tgt_sh: float | None,
    nature_of_bid: str | None,
    percent_owned_sought: float | None,
    status: str | None,
    notes: str | None,
    raw_deal_json: str | None,
) -> int:
    """
    Insert one M&A event row and return its ID.
    """
    cursor = conn.execute(
        """
        INSERT INTO mna_events (
            bbg_deal_id,
            target_company_id,
            acquirer_company_id,
            announcement_date,
            expected_completion_date,
            effective_date,
            index_implementation_date,
            deal_type,
            payment_type,
            offer_price,
            offer_currency,
            cash_terms_per_tgt_sh,
            stock_terms_acq_sh_per_tgt_sh,
            nature_of_bid,
            percent_owned_sought,
            status,
            notes,
            raw_deal_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            bbg_deal_id,
            target_company_id,
            acquirer_company_id,
            announcement_date,
            expected_completion_date,
            effective_date,
            index_implementation_date,
            deal_type,
            payment_type,
            offer_price,
            offer_currency,
            cash_terms_per_tgt_sh,
            stock_terms_acq_sh_per_tgt_sh,
            nature_of_bid,
            percent_owned_sought,
            status,
            notes,
            raw_deal_json,
        ),
    )
    return int(cursor.lastrowid)


def upsert_ownership_snapshot(
    conn: sqlite3.Connection,
    company_id: int,
    shareholder_id: int,
    snapshot_date: str,
    rank: int | None,
    shares_held: float | None,
    ownership_pct: float | None,
    source: str | None,
) -> None:
    """
    Insert/update an ownership snapshot.
    """
    conn.execute(
        """
        INSERT INTO ownership_snapshots (
            company_id,
            shareholder_id,
            snapshot_date,
            rank,
            shares_held,
            ownership_pct,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id, shareholder_id, snapshot_date) DO UPDATE SET
            rank = excluded.rank,
            shares_held = excluded.shares_held,
            ownership_pct = excluded.ownership_pct,
            source = COALESCE(excluded.source, ownership_snapshots.source)
        """,
        (
            company_id,
            shareholder_id,
            snapshot_date,
            rank,
            shares_held,
            ownership_pct,
            source,
        ),
    )


def upsert_price_rows(
    conn: sqlite3.Connection,
    company_id: int,
    rows: Iterable[dict[str, Any]],
) -> None:
    """
    Insert/update multiple price rows for one company.
    Each row should contain:
    - date
    - open
    - high
    - low
    - close
    - adjusted_close
    - currency
    """
    conn.executemany(
        """
        INSERT INTO prices (
            company_id,
            price_date,
            open,
            high,
            low,
            close,
            adjusted_close,
            currency
        )
        VALUES (:company_id, :date, :open, :high, :low, :close, :adjusted_close, :currency)
        ON CONFLICT(company_id, price_date) DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            adjusted_close = excluded.adjusted_close,
            currency = COALESCE(excluded.currency, prices.currency)
        """,
        ({**row, "company_id": company_id} for row in rows),
    )


def upsert_volume_rows(
    conn: sqlite3.Connection,
    company_id: int,
    rows: Iterable[dict[str, Any]],
) -> None:
    """
    Insert/update multiple volume rows for one company.
    Each row should contain:
    - date
    - volume
    """
    conn.executemany(
        """
        INSERT INTO volumes (
            company_id,
            volume_date,
            volume
        )
        VALUES (:company_id, :date, :volume)
        ON CONFLICT(company_id, volume_date) DO UPDATE SET
            volume = excluded.volume
        """,
        ({**row, "company_id": company_id} for row in rows),
    )


def save_analysis_output(
    conn: sqlite3.Connection,
    event_id: int,
    analysis_type: str,
    output: dict[str, Any],
) -> int:
    """
    Save analysis output as JSON and return its ID.
    """
    cursor = conn.execute(
        """
        INSERT INTO analysis_outputs (
            event_id,
            analysis_type,
            output_json
        )
        VALUES (?, ?, ?)
        """,
        (event_id, analysis_type, json.dumps(output, indent=2, sort_keys=True)),
    )
    return int(cursor.lastrowid)