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
