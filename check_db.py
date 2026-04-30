from pathlib import Path
from ma_index_tracker.db.database import connect

DB_PATH = Path(__file__).resolve().parent / "ma_index_tracker.sqlite"

COUNTS_QUERY = """
SELECT
    c.id,
    c.ticker,
    (SELECT COUNT(*) FROM prices p WHERE p.company_id = c.id) AS price_rows,
    (SELECT COUNT(*) FROM volumes v WHERE v.company_id = c.id) AS volume_rows
FROM companies c
ORDER BY c.id
"""

with connect(DB_PATH) as conn:
    print("COMPANIES")
    for row in conn.execute("SELECT * FROM companies ORDER BY id").fetchall():
        print(dict(row))

    print("\nMNA EVENTS")
    for row in conn.execute("SELECT * FROM mna_events ORDER BY id").fetchall():
        print(dict(row))

    print("\nTOTAL COUNTS")
    print("prices:", conn.execute("SELECT COUNT(*) AS n FROM prices").fetchone()["n"])
    print("volumes:", conn.execute("SELECT COUNT(*) AS n FROM volumes").fetchone()["n"])

    print("\nPRICE SAMPLE")
    for row in conn.execute("SELECT * FROM prices ORDER BY price_date LIMIT 5").fetchall():
        print(dict(row))

    print("\nVOLUME SAMPLE")
    for row in conn.execute("SELECT * FROM volumes ORDER BY volume_date LIMIT 5").fetchall():
        print(dict(row))

    print("\nROWS PER COMPANY")
    for row in conn.execute(COUNTS_QUERY).fetchall():
        print(dict(row))