from __future__ import annotations

import json
import re
from pathlib import Path

from ma_index_tracker.bloomberg_client import BloombergClient
from ma_index_tracker.bulk_loader import resolve_company_to_ticker
from ma_index_tracker.db.database import connect, upsert_company

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
    return str(name).strip()


def is_multi_party_or_nonstandard(name: str) -> bool:
    text = name.strip()

    # clear multi-buyer / consortium cases
    if "," in text:
        return True

    # cases we do not want to auto-resolve in this first pass
    bad_patterns = [
        r"\bPrivate Investor\b",
        r"\bDepartment\b",
        r"\bAuthority\b",
        r"\bGovernment\b",
        r"\bFund\b",
        r"\bRetirement System\b",
        r"\bPension\b",
        r"\bPublic Investment Fund\b",
        r"\bCorp\s*\(Fund:",
        r"\bLLC\s*\(Fund:",
    ]

    for pat in bad_patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            return True

    return False


def clean_lookup_name(name: str) -> str:
    """
    Light cleanup only. Keep the identity intact.
    """
    text = name.strip()
    text = re.sub(r"\(.*?\)", " ", text)  # remove bracketed fund notes etc
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main() -> None:
    query = """
    SELECT
        e.id AS event_id,
        e.raw_deal_json,
        e.acquirer_company_id,
        e.status,
        e.payment_type,
        target.name AS target_name
    FROM mna_events e
    JOIN companies target
        ON e.target_company_id = target.id
    WHERE e.acquirer_company_id IS NULL
    ORDER BY e.id
    """

    client = BloombergClient()

    enriched = []
    skipped = []
    failed = []

    # optional manual overrides for tricky names
    ticker_overrides = {
        # example:
        # "International Business Machine": "IBM US Equity",
        # "Sanofi": "SAN FP Equity",
    }

    with connect(DB_PATH) as conn:
        rows = [dict(r) for r in conn.execute(query).fetchall()]

        for row in rows:
            event_id = row["event_id"]
            csv_acquirer_name = extract_csv_acquirer_name(row["raw_deal_json"])

            if not csv_acquirer_name:
                skipped.append(
                    {
                        "event_id": event_id,
                        "reason": "no_csv_acquirer_name",
                        "target_name": row["target_name"],
                    }
                )
                continue

            if is_multi_party_or_nonstandard(csv_acquirer_name):
                skipped.append(
                    {
                        "event_id": event_id,
                        "reason": "multi_party_or_nonstandard",
                        "target_name": row["target_name"],
                        "csv_acquirer_name": csv_acquirer_name,
                    }
                )
                continue

            lookup_name = clean_lookup_name(csv_acquirer_name)

            try:
                ticker = (
                    ticker_overrides.get(csv_acquirer_name)
                    or ticker_overrides.get(lookup_name)
                    or resolve_company_to_ticker(client, lookup_name)
                )

                ref = client.reference_data(
                    security=ticker,
                    fields=["NAME", "COUNTRY_ISO", "INDUSTRY_SECTOR"],
                )

                acquirer_company_id = upsert_company(
                    conn=conn,
                    ticker=ticker,
                    name=ref.get("NAME") or csv_acquirer_name,
                    exchange=None,
                    country=ref.get("COUNTRY_ISO"),
                    sector=ref.get("INDUSTRY_SECTOR"),
                )

                conn.execute(
                    """
                    UPDATE mna_events
                    SET acquirer_company_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (acquirer_company_id, event_id),
                )

                conn.commit()

                enriched.append(
                    {
                        "event_id": event_id,
                        "target_name": row["target_name"],
                        "csv_acquirer_name": csv_acquirer_name,
                        "resolved_ticker": ticker,
                        "resolved_name": ref.get("NAME"),
                    }
                )
                print(
                    f"[OK] event {event_id}: {row['target_name']} -> "
                    f"{csv_acquirer_name} -> {ticker}"
                )

            except Exception as e:
                conn.rollback()
                failed.append(
                    {
                        "event_id": event_id,
                        "target_name": row["target_name"],
                        "csv_acquirer_name": csv_acquirer_name,
                        "error": str(e),
                    }
                )
                print(
                    f"[FAIL] event {event_id}: {row['target_name']} -> "
                    f"{csv_acquirer_name} -> {e}"
                )

    print("\nENRICHMENT SUMMARY")
    print(
        {
            "enriched_count": len(enriched),
            "skipped_count": len(skipped),
            "failed_count": len(failed),
        }
    )

    print("\nENRICHED SAMPLE")
    for row in enriched[:20]:
        print(row)

    print("\nSKIPPED SAMPLE")
    for row in skipped[:20]:
        print(row)

    print("\nFAILED SAMPLE")
    for row in failed[:20]:
        print(row)


if __name__ == "__main__":
    main()