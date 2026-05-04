from __future__ import annotations

import statistics
from typing import Any

from ma_index_tracker.analysis import compute_target_analysis
from ma_index_tracker.analogues import compute_analogue_selection
from ma_index_tracker.db.database import save_analysis_output
from ma_index_tracker.spread_analysis import compute_spread_analysis


def _safe_median(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.median(values)


def _safe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _within_event_window(
    rows: list[dict[str, Any]],
    *,
    min_event_day: int,
    max_event_day: int,
) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        event_day = row.get("event_day")
        if event_day is None:
            continue
        if min_event_day <= int(event_day) <= max_event_day:
            out.append(row)
    return out


def _aggregate_series_by_event_day(
    per_event_series: list[dict[str, Any]],
    value_key: str,
    *,
    min_event_day: int,
    max_event_day: int,
) -> list[dict[str, Any]]:
    """
    Aggregate rows from multiple events by event_day within a fixed window.
    Returns one row per event_day with median/mean/count.
    """
    bucket: dict[int, list[float]] = {}

    for event_result in per_event_series:
        rows = _within_event_window(
            event_result.get("rows", []),
            min_event_day=min_event_day,
            max_event_day=max_event_day,
        )
        for row in rows:
            event_day = row.get("event_day")
            value = row.get(value_key)
            if event_day is None or value is None:
                continue
            bucket.setdefault(int(event_day), []).append(float(value))

    out = []
    for event_day in sorted(bucket):
        values = bucket[event_day]
        out.append(
            {
                "event_day": event_day,
                "count": len(values),
                "median": _safe_median(values),
                "mean": _safe_mean(values),
            }
        )
    return out


def _lookup_day(rows: list[dict[str, Any]], event_day: int) -> dict[str, Any] | None:
    for row in rows:
        if row.get("event_day") == event_day:
            return row
    return None


def _lookup_day_value(rows: list[dict[str, Any]], event_day: int, key: str) -> float | None:
    row = _lookup_day(rows, event_day)
    if row is None:
        return None
    value = row.get(key)
    if value is None:
        return None
    return float(value)


def _latest_non_null_event_day_in_window(
    rows: list[dict[str, Any]],
    key: str,
    *,
    min_event_day: int,
    max_event_day: int,
) -> int | None:
    valid_days = [
        int(r["event_day"])
        for r in rows
        if r.get("event_day") is not None
        and r.get(key) is not None
        and min_event_day <= int(r["event_day"]) <= max_event_day
    ]
    if not valid_days:
        return None
    return max(valid_days)


def _trim_analysis_rows(
    analysis_result: dict[str, Any],
    *,
    min_event_day: int,
    max_event_day: int,
) -> dict[str, Any]:
    """
    Return a shallow copy with rows limited to the chosen event window.
    """
    trimmed = dict(analysis_result)
    trimmed["rows"] = _within_event_window(
        analysis_result.get("rows", []),
        min_event_day=min_event_day,
        max_event_day=max_event_day,
    )
    return trimmed


def compute_analogue_comparison(
    conn,
    pending_event_id: int,
    top_k: int = 10,
    min_event_day: int = -5,
    max_event_day: int = 60,
) -> dict[str, Any]:
    """
    Build comparison between a pending deal and its selected analogue set.

    Returns:
    - analogue selection metadata
    - pending target/spread analyses (windowed)
    - per-analogue analyses (windowed)
    - aggregated analogue paths within fixed event window
    - headline comparisons
    """
    analogue_selection = compute_analogue_selection(conn, pending_event_id, top_k=top_k)

    pending_target_analysis_full = compute_target_analysis(conn, pending_event_id)
    pending_spread_analysis_full = compute_spread_analysis(conn, pending_event_id)

    pending_target_analysis = _trim_analysis_rows(
        pending_target_analysis_full,
        min_event_day=min_event_day,
        max_event_day=max_event_day,
    )
    pending_spread_analysis = _trim_analysis_rows(
        pending_spread_analysis_full,
        min_event_day=min_event_day,
        max_event_day=max_event_day,
    )

    analogue_event_ids = [a["event_id"] for a in analogue_selection["analogues"]]

    analogue_target_analyses = []
    analogue_spread_analyses = []

    analogue_meta_by_event_id = {
        a["event_id"]: a for a in analogue_selection["analogues"]
    }

    for analogue_event_id in analogue_event_ids:
        analogue_target_full = compute_target_analysis(conn, analogue_event_id)
        analogue_spread_full = compute_spread_analysis(conn, analogue_event_id)

        analogue_target = _trim_analysis_rows(
            analogue_target_full,
            min_event_day=min_event_day,
            max_event_day=max_event_day,
        )
        analogue_spread = _trim_analysis_rows(
            analogue_spread_full,
            min_event_day=min_event_day,
            max_event_day=max_event_day,
        )

        analogue_target_analyses.append(
            {
                "event_id": analogue_event_id,
                "analogue_meta": analogue_meta_by_event_id[analogue_event_id],
                **analogue_target,
            }
        )
        analogue_spread_analyses.append(
            {
                "event_id": analogue_event_id,
                "analogue_meta": analogue_meta_by_event_id[analogue_event_id],
                **analogue_spread,
            }
        )

    analogue_target_return_agg = _aggregate_series_by_event_day(
        analogue_target_analyses,
        "return_from_baseline",
        min_event_day=min_event_day,
        max_event_day=max_event_day,
    )
    analogue_volume_ratio_agg = _aggregate_series_by_event_day(
        analogue_target_analyses,
        "volume_ratio",
        min_event_day=min_event_day,
        max_event_day=max_event_day,
    )
    analogue_spread_abs_agg = _aggregate_series_by_event_day(
        analogue_spread_analyses,
        "spread_abs",
        min_event_day=min_event_day,
        max_event_day=max_event_day,
    )
    analogue_spread_pct_agg = _aggregate_series_by_event_day(
        analogue_spread_analyses,
        "spread_pct",
        min_event_day=min_event_day,
        max_event_day=max_event_day,
    )

    pending_latest_spread_day = _latest_non_null_event_day_in_window(
        pending_spread_analysis["rows"],
        "spread_abs",
        min_event_day=min_event_day,
        max_event_day=max_event_day,
    )

    headline_comparison = {
        "comparison_window": {
            "min_event_day": min_event_day,
            "max_event_day": max_event_day,
        },
        "pending_announcement_jump": pending_target_analysis.get("announcement_jump"),
        "analogue_median_announcement_jump": _lookup_day_value(
            analogue_target_return_agg, 0, "median"
        ),
        "analogue_mean_announcement_jump": _lookup_day_value(
            analogue_target_return_agg, 0, "mean"
        ),
        "pending_day_5_return": _lookup_day_value(
            pending_target_analysis["rows"], 5, "return_from_baseline"
        ),
        "analogue_median_day_5_return": _lookup_day_value(
            analogue_target_return_agg, 5, "median"
        ),
        "analogue_mean_day_5_return": _lookup_day_value(
            analogue_target_return_agg, 5, "mean"
        ),
        "pending_announcement_day_spread_abs": pending_spread_analysis.get(
            "announcement_day_spread_abs"
        ),
        "analogue_median_announcement_day_spread_abs": _lookup_day_value(
            analogue_spread_abs_agg, 0, "median"
        ),
        "analogue_mean_announcement_day_spread_abs": _lookup_day_value(
            analogue_spread_abs_agg, 0, "mean"
        ),
        "pending_announcement_day_spread_pct": pending_spread_analysis.get(
            "announcement_day_spread_pct"
        ),
        "analogue_median_announcement_day_spread_pct": _lookup_day_value(
            analogue_spread_pct_agg, 0, "median"
        ),
        "analogue_mean_announcement_day_spread_pct": _lookup_day_value(
            analogue_spread_pct_agg, 0, "mean"
        ),
        "pending_latest_spread_event_day": pending_latest_spread_day,
        "pending_latest_spread_abs": (
            _lookup_day_value(pending_spread_analysis["rows"], pending_latest_spread_day, "spread_abs")
            if pending_latest_spread_day is not None
            else None
        ),
        "analogue_median_latest_spread_abs_same_day": (
            _lookup_day_value(analogue_spread_abs_agg, pending_latest_spread_day, "median")
            if pending_latest_spread_day is not None
            else None
        ),
        "analogue_mean_latest_spread_abs_same_day": (
            _lookup_day_value(analogue_spread_abs_agg, pending_latest_spread_day, "mean")
            if pending_latest_spread_day is not None
            else None
        ),
        "pending_latest_spread_pct": (
            _lookup_day_value(pending_spread_analysis["rows"], pending_latest_spread_day, "spread_pct")
            if pending_latest_spread_day is not None
            else None
        ),
        "analogue_median_latest_spread_pct_same_day": (
            _lookup_day_value(analogue_spread_pct_agg, pending_latest_spread_day, "median")
            if pending_latest_spread_day is not None
            else None
        ),
        "analogue_mean_latest_spread_pct_same_day": (
            _lookup_day_value(analogue_spread_pct_agg, pending_latest_spread_day, "mean")
            if pending_latest_spread_day is not None
            else None
        ),
    }

    result = {
        "pending_event_id": pending_event_id,
        "comparison_window": {
            "min_event_day": min_event_day,
            "max_event_day": max_event_day,
        },
        "analogue_selection": analogue_selection,
        "pending_target_analysis": pending_target_analysis,
        "pending_spread_analysis": pending_spread_analysis,
        "analogue_target_analyses": analogue_target_analyses,
        "analogue_spread_analyses": analogue_spread_analyses,
        "aggregated_analogue_paths": {
            "target_return_from_baseline": analogue_target_return_agg,
            "target_volume_ratio": analogue_volume_ratio_agg,
            "spread_abs": analogue_spread_abs_agg,
            "spread_pct": analogue_spread_pct_agg,
        },
        "headline_comparison": headline_comparison,
    }

    return result


def save_analogue_comparison(
    conn,
    pending_event_id: int,
    top_k: int = 10,
    min_event_day: int = -5,
    max_event_day: int = 60,
) -> int:
    result = compute_analogue_comparison(
        conn,
        pending_event_id,
        top_k=top_k,
        min_event_day=min_event_day,
        max_event_day=max_event_day,
    )
    analysis_id = save_analysis_output(
        conn=conn,
        event_id=pending_event_id,
        analysis_type="analogue_comparison",
        output=result,
    )
    return analysis_id