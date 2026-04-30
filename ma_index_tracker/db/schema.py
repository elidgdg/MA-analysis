"""SQLite schema used by the M&A index tracker."""

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    name TEXT,
    exchange TEXT,
    country TEXT,
    sector TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mna_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_company_id INTEGER NOT NULL,
    acquirer_company_id INTEGER,
    announcement_date TEXT,
    effective_date TEXT,
    index_implementation_date TEXT,
    deal_type TEXT,
    offer_price REAL,
    offer_currency TEXT,
    status TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (target_company_id) REFERENCES companies(id),
    FOREIGN KEY (acquirer_company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS shareholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    holder_type TEXT,
    country TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ownership_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    shareholder_id INTEGER NOT NULL,
    snapshot_date TEXT,
    rank INTEGER,
    shares_held REAL,
    ownership_pct REAL,
    source TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (shareholder_id) REFERENCES shareholders(id),
    UNIQUE (company_id, shareholder_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    price_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adjusted_close REAL,
    currency TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE (company_id, price_date)
);

CREATE TABLE IF NOT EXISTS volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    volume_date TEXT NOT NULL,
    volume REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE (company_id, volume_date)
);

CREATE TABLE IF NOT EXISTS analysis_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    analysis_type TEXT NOT NULL,
    output_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES mna_events(id)
);

CREATE INDEX IF NOT EXISTS idx_mna_events_target ON mna_events(target_company_id);
CREATE INDEX IF NOT EXISTS idx_prices_company_date ON prices(company_id, price_date);
CREATE INDEX IF NOT EXISTS idx_volumes_company_date ON volumes(company_id, volume_date);
"""
