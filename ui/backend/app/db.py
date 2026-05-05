from __future__ import annotations

from pathlib import Path


def get_project_root() -> Path:
    """
    Returns the MA-analysis project root.

    File location:
    MA-analysis/ui/backend/app/db.py

    parents[0] = app
    parents[1] = backend
    parents[2] = ui
    parents[3] = MA-analysis
    """
    return Path(__file__).resolve().parents[3]


def get_db_path() -> Path:
    return get_project_root() / "ma_index_tracker.sqlite"