import sqlite3

conn = sqlite3.connect("flight_quotes.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM flight_quotes ORDER BY id").fetchall()

print(f"Total records in DB: {len(rows)}")
print("-" * 100)
for r in rows:
    print(
        f"ID:{r['id']:02d} | {r['flight_number']:10} | {r['airline'][:18]:18} | "
        f"{r['origin_sector']}>{r['destination_sector']} | "
        f"Rs.{r['total_fare']:>9.2f} | {r['seat_status']:10} | "
        f"MathOK:{bool(r['is_math_valid'])} | Outlier:{bool(r['is_price_outlier'])} | "
        f"{r['source_file']}"
    )

print("-" * 100)
print()

# Summary stats
fares = [r["total_fare"] for r in rows]
print(f"Min fare : Rs.{min(fares):,.2f}")
print(f"Max fare : Rs.{max(fares):,.2f}")
print(f"Avg fare : Rs.{sum(fares)/len(fares):,.2f}")
print(f"Math valid   : {sum(1 for r in rows if r['is_math_valid'])}/{len(rows)}")
print(f"Outliers     : {sum(1 for r in rows if r['is_price_outlier'])}/{len(rows)}")

conn.close()
