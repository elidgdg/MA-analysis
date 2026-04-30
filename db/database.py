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