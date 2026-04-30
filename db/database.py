from __future__ import annotations
import json
import sqlite3
from pathlib import Path

from .schema import SCHEMA_SQL

def connect(db_path: Path) -> sqlite3.Connection:
    """Connect to the SQLite database, creating it if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # make res results dict-like
    conn.execute("PRAGMA foreign_keys = ON;") # enable foreign key constraints
    return conn

def init_db(db_path: Path) -> None:
    """Initialize the database with the required schema."""
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)


def upinsert_company(
    conn: sqlite3.Connection,
    ticker: str,
    name: str | None = None,
    exchange: str | None = None,
    country: str | None = None,
    sector: str | None = None
) -> Int:
    """Insert/update a company record and return its ID."""
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
        (ticker, name, exchange, country, sector)
    )
    row = conn.execute(
        "SELECT id FROM companies WHERE ticker = ?",
        (ticker,)
    ).fetchone()
    return int(row["id"])

def upinsert_shareholder(
    conn: sqlite3.Connection,
    name: str,
    holder_type: str | None = None,
    country: str | None = None
) -> Int:
    """Insert/update a shareholder record and return its ID."""
    conn.execute(
        """
        INSERT INTO shareholders (name, holder_type, country)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            holder_type = COALESCE(excluded.holder_type, shareholders.holder_type),
            country = COALESCE(excluded.country, shareholders.country)
        """,
        (name, holder_type, country)
    )
    row = conn.execute(
        "SELECT id FROM shareholders WHERE name = ?",
        (name,)
    ).fetchone()
    return int(row["id"])

def insert_ma_event(
    conn: sqlite3.Connection,
    target_company_id: int,
    acquirer_company_id: int | None,
    announcement_date: str | None,
    effective_date: str | None,
    index_implementation_date: str | None,
    deal_type: str | None,
    offer_price: float | None,
    offer_currency: str | None,
    status: str | None,
    notes: str | None
) -> int:
    """Insert a new M&A event and return its ID."""
    cursor = conn.execute(
        """
        INSERT INTO mna_events (
            target_company_id, acquirer_company_id, announcement_date,
            effective_date, index_implementation_date, deal_type,
            offer_price, offer_currency, status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            target_company_id, acquirer_company_id, announcement_date,
            effective_date, index_implementation_date, deal_type,
            offer_price, offer_currency, status, notes
        )
    )
    return int(cursor.lastrowid)

def upinsert_ownership_snapshot(
    conn: sqlite3.Connection,
    company_id: int,
    shareholder_id: int,
    snapshot_date: str,
    rank: int | None,
    shares_held: float | None,
    ownership_pct: float | None,
    source: str | None
) -> None:
    """Insert/update an ownership snapshot record."""

    conn.execute(
        """
        INSERT INTO ownership_snapshots (
            company_id, shareholder_id, snapshot_date, rank,
            shares_held, ownership_pct, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id, shareholder_id, snapshot_date) DO UPDATE SET
            rank = excluded.rank,
            shares_held = excluded.shares_held,
            ownership_pct = excluded.ownership_pct,
            source = COALESCE(excluded.source, ownership_snapshots.source),
        """,
        (
            company_id, shareholder_id, snapshot_date, rank, shares_held, ownership_pct, source
        )
    )