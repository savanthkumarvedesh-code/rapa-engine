"""
sync_mockair_to_flight_quotes.py
Synchronizes scraped fare quotes from MockAir Network directly into flight_quotes.db
for the FastAPI /api/v1/quotes and portal dashboard endpoints.
"""

import sqlite3
import os
import sys
import json
from datetime import datetime

RAPA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAPA_DIR not in sys.path:
    sys.path.insert(0, RAPA_DIR)

from fares.mockair_scraper import get_mockair_scraper, AIRLINE_IDS

DB_PATH = os.path.join(RAPA_DIR, "flight_quotes.db")

TRUNK_ROUTES = [
    ("DEL", "BOM"),
    ("DEL", "BLR"),
    ("BOM", "BLR"),
    ("DEL", "CCU"),
    ("BLR", "HYD"),
    ("MAA", "DEL")
]

HORIZONS = [1, 7, 15, 30, 45]


def sync():
    print("[SYNC] Connecting to flight_quotes.db...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS flight_quotes (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_number        TEXT    NOT NULL,
        airline              TEXT    NOT NULL,
        origin_sector        TEXT    NOT NULL,
        destination_sector   TEXT    NOT NULL,
        departure_timestamp  TEXT    NOT NULL,
        base_fare            REAL    NOT NULL,
        taxes                REAL    NOT NULL,
        user_development_fee REAL    NOT NULL,
        convenience_charge   REAL    NOT NULL,
        total_fare           REAL    NOT NULL,
        seat_status          TEXT    NOT NULL DEFAULT 'available',
        is_math_valid        INTEGER NOT NULL DEFAULT 1,
        is_price_outlier     INTEGER NOT NULL DEFAULT 0,
        is_duplicate         INTEGER NOT NULL DEFAULT 0,
        source_type          TEXT    DEFAULT 'mockair_target',
        ota_platform         TEXT    DEFAULT 'MockAir_Network',
        fare_class           TEXT    DEFAULT 'Economy',
        source_file          TEXT    DEFAULT 'mockair_live_scraper',
        ingestion_timestamp  TEXT    DEFAULT CURRENT_TIMESTAMP
    );
    """)

    scraper = get_mockair_scraper()
    total_inserted = 0

    for orig, dest in TRUNK_ROUTES:
        for h in HORIZONS:
            dep_date = datetime.now().strftime("%Y-%m-%d")
            quotes = scraper.harvest_corridor(orig, dest, dep_date, f"T+{h}")
            for q in quotes:
                raw_data = json.loads(q.raw_payload or "{}")
                taxes = float(raw_data.get("taxes", 850))
                udf = float(raw_data.get("udf", 200))
                conv = float(raw_data.get("convenience_fee", 350))
                base = float(q.base_fare or (q.total_fare - taxes - udf - conv))
                total = float(q.total_fare)
                airline_name = raw_data.get("airline", q.carrier_code)

                # Validation checks
                calc_sum = round(base + taxes + udf + conv, 2)
                is_math_valid = 1 if abs(calc_sum - total) <= 0.05 else 0

                cur.execute("""
                INSERT INTO flight_quotes (
                    flight_number, airline, origin_sector, destination_sector,
                    departure_timestamp, base_fare, taxes, user_development_fee,
                    convenience_charge, total_fare, seat_status, is_math_valid,
                    is_price_outlier, is_duplicate, source_type, ota_platform,
                    fare_class, source_file, ingestion_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available', ?, 0, 0, 'mockair_target', 'MockAir_Network', 'Economy', 'live_stream', ?);
                """, (
                    q.flight_number,
                    airline_name,
                    q.origin,
                    q.destination,
                    q.departure_date,
                    base,
                    taxes,
                    udf,
                    conv,
                    total,
                    is_math_valid,
                    datetime.now().isoformat()
                ))
                total_inserted += 1

    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM flight_quotes").fetchone()[0]
    conn.close()

    print(f"[SYNC] Ingested {total_inserted} live MockAir quotes. Total records in flight_quotes.db: {count}")


if __name__ == "__main__":
    sync()
