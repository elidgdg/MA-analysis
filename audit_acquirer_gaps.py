from __future__ import annotations

import json
from pathlib import Path

from ma_index_tracker.db.database import connect

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"


def extract_csv_acquirer_name(raw_deal_json: str | None) -> str | None:
    if not raw_deal_json:
        return None
    try:
        payload = json.loads(raw_deal_json)
    except Exception:
        return None

    csv_row = payload.get("csv_row", {})
    name = csv_row.get("acquirer_name")
    if name in (None, "", "--"):
        return None
    return str(name)


def main() -> None:
    query = """
    SELECT
        e.id AS event_id,
        e.status,
        e.payment_type,
        e.acquirer_company_id,
        e.raw_deal_json,
        target.name AS target_name,
        acquirer.name AS acquirer_name,
        acquirer.ticker AS acquirer_ticker
    FROM mna_events e
    JOIN companies target
        ON e.target_company_id = target.id
    LEFT JOIN companies acquirer
        ON e.acquirer_company_id = acquirer.id
    ORDER BY e.id
    """

    with connect(DB_PATH) as conn:
        rows = [dict(r) for r in conn.execute(query).fetchall()]

    total = len(rows)
    missing_name = 0
    missing_company_link = 0
    csv_fallback_available = 0

    problem_rows = []

    for row in rows:
        csv_acquirer_name = extract_csv_acquirer_name(row["raw_deal_json"])

        has_name = row["acquirer_name"] not in (None, "", "--")
        has_company_link = row["acquirer_company_id"] is not None

        if not has_name:
            missing_name += 1

        if not has_company_link:
            missing_company_link += 1

        if (not has_name) and csv_acquirer_name:
            csv_fallback_available += 1

        if (not has_name) or (not has_company_link):
            problem_rows.append(
                {
                    "event_id": row["event_id"],
                    "status": row["status"],
                    "payment_type": row["payment_type"],
                    "target_name": row["target_name"],
                    "acquirer_name": row["acquirer_name"],
                    "acquirer_ticker": row["acquirer_ticker"],
                    "acquirer_company_id": row["acquirer_company_id"],
                    "csv_acquirer_name": csv_acquirer_name,
                }
            )

    print("ACQUIRER GAP SUMMARY")
    print(
        {
            "total_events": total,
            "missing_acquirer_name": missing_name,
            "missing_acquirer_company_link": missing_company_link,
            "csv_fallback_available_for_missing_name": csv_fallback_available,
        }
    )

    print("\nPROBLEM ROW SAMPLE")
    for row in problem_rows[:30]:
        print(row)


if __name__ == "__main__":
    main()