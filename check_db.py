import sqlite3
from datetime import datetime

DB = "data/rapa.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 60)
print("RAPA DATABASE AUDIT")
print("=" * 60)

# Table sizes
for table in ["fare_quotes", "index_values", "cpi_benchmarks", "ingestion_logs"]:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"{table:25s}: {cur.fetchone()[0]:,} records")

print()

# Date range and unique days in fare_quotes
cur.execute("""
    SELECT
        MIN(quote_timestamp) AS first_seen,
        MAX(quote_timestamp) AS last_seen,
        COUNT(DISTINCT DATE(quote_timestamp)) AS unique_days_collected,
        COUNT(DISTINCT departure_date) AS unique_departure_dates,
        COUNT(DISTINCT route) AS routes,
        COUNT(DISTINCT advance_window) AS horizons,
        COUNT(DISTINCT carrier_code) AS carriers
    FROM fare_quotes
""")
row = dict(cur.fetchone())
print("FARE QUOTES SUMMARY")
print("-" * 60)
for k, v in row.items():
    print(f"  {k:35s}: {v}")

print()

# Per-day breakdown (days when data was actually collected)
cur.execute("""
    SELECT DATE(quote_timestamp) AS day, COUNT(*) AS quotes
    FROM fare_quotes
    GROUP BY day
    ORDER BY day
""")
days = cur.fetchall()
print(f"COLLECTION DAYS ({len(days)} total days with data):")
print("-" * 60)
for d in days:
    print(f"  {d['day']}  →  {d['quotes']:,} quotes")

print()

# Departure date coverage
cur.execute("""
    SELECT departure_date, COUNT(*) AS quotes, COUNT(DISTINCT route) AS routes
    FROM fare_quotes
    GROUP BY departure_date
    ORDER BY departure_date
    LIMIT 20
""")
print("DEPARTURE DATE COVERAGE (first 20):")
print("-" * 60)
for d in cur.fetchall():
    print(f"  dep={d['departure_date']}  {d['routes']} routes  {d['quotes']:,} quotes")

print()

# Route + horizon matrix
cur.execute("""
    SELECT route, advance_window, COUNT(*) as n
    FROM fare_quotes
    GROUP BY route, advance_window
    ORDER BY route, advance_window
""")
print("ROUTE x HORIZON MATRIX:")
print("-" * 60)
prev_route = None
for row in cur.fetchall():
    if row['route'] != prev_route:
        print(f"  {row['route']}")
        prev_route = row['route']
    print(f"    {row['advance_window']:8s}  →  {row['n']:,} quotes")

conn.close()
print()
print("=" * 60)