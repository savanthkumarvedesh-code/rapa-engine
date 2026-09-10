"""
SQLite Database Schema and Access Layer for RAPA Engine.
Manages:
1. cpi_benchmarks: MoSPI official CPI benchmark time-series (Airfare & Transport).
2. ingestion_logs: Truthful audit trail for every ingestion attempt (success or error).
3. fare_quotes: Scaffolding for route-level quotes.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapa.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Creates database tables if they do not exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Ingestion Logs: Honest audit trail for every operation
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingestion_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        operation TEXT NOT NULL,
        status TEXT NOT NULL,
        records_ingested INTEGER DEFAULT 0,
        details_json TEXT,
        trigger_type TEXT DEFAULT 'manual',
        timestamp TEXT NOT NULL
    );
    """)

    try:
        cursor.execute("ALTER TABLE ingestion_logs ADD COLUMN trigger_type TEXT DEFAULT 'manual';")
    except Exception:
        pass

    # 2. CPI Benchmarks: Official NSO / MoSPI aggregate figures
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cpi_benchmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        base_year TEXT NOT NULL,
        series TEXT NOT NULL,
        year INTEGER NOT NULL,
        month TEXT NOT NULL,
        state TEXT NOT NULL,
        sector TEXT NOT NULL,
        division TEXT,
        group_name TEXT,
        sub_class TEXT,
        item_name TEXT,
        item_code TEXT,
        cpi_index REAL NOT NULL,
        inflation REAL,
        imputation TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(base_year, year, month, state, sector, item_code) ON CONFLICT REPLACE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fare_quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_timestamp TEXT NOT NULL,
        source TEXT NOT NULL,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        route TEXT NOT NULL,
        carrier_code TEXT NOT NULL,
        flight_number TEXT NOT NULL,
        departure_date TEXT NOT NULL,
        advance_window TEXT NOT NULL,
        base_fare REAL,
        total_fare REAL NOT NULL,
        currency TEXT DEFAULT 'INR',
        raw_payload TEXT,
        fare_class TEXT DEFAULT 'UNKNOWN',
        is_duplicate INTEGER NOT NULL DEFAULT 0
    );
    """)

    # Safe migration for existing fare_quotes databases
    try:
        cursor.execute("ALTER TABLE fare_quotes ADD COLUMN fare_class TEXT DEFAULT 'UNKNOWN'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE fare_quotes ADD COLUMN is_duplicate INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass

    # 4. High-Frequency Index Values
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS index_values (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        calculation_date TEXT NOT NULL,
        base_date TEXT NOT NULL,
        frequency TEXT NOT NULL,
        jevons_index REAL NOT NULL,
        naive_index REAL NOT NULL,
        inflation_mom REAL,
        match_rate_pct REAL,
        matched_items_count INTEGER,
        base_items_count INTEGER,
        target_items_count INTEGER,
        route_breakdown_json TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 5. Scheduler Runs: APScheduler state telemetry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheduler_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        last_run_at TEXT,
        next_run_at TEXT,
        status TEXT NOT NULL DEFAULT 'idle',
        cycle_result TEXT,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpi_item_year ON cpi_benchmarks (item_name, year, month);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpi_state_sector ON cpi_benchmarks (state, sector);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fare_route_date ON fare_quotes (route, departure_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_index_calc_date ON index_values (calculation_date);")


    conn.commit()
    conn.close()


def log_ingestion(
    source: str,
    operation: str,
    status: str,
    records_ingested: int = 0,
    details: Optional[Dict[str, Any]] = None,
    db_path: str = DB_PATH,
    trigger_type: Optional[str] = None
) -> int:
    """Inserts a truthful, queryable audit record of an ingestion run."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        t_type = trigger_type or (details.get("trigger_type") if details else None) or "manual"
        
        # Check if trigger_type column exists
        cursor.execute("PRAGMA table_info(ingestion_logs);")
        cols = [r["name"] for r in cursor.fetchall()]
        
        if "trigger_type" in cols:
            cursor.execute("""
            INSERT INTO ingestion_logs (source, operation, status, records_ingested, details_json, trigger_type, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                source,
                operation,
                status,
                records_ingested,
                json.dumps(details or {}),
                t_type,
                datetime.now().isoformat()
            ))
        else:
            cursor.execute("""
            INSERT INTO ingestion_logs (source, operation, status, records_ingested, details_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                source,
                operation,
                status,
                records_ingested,
                json.dumps(details or {}),
                datetime.now().isoformat()
            ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def insert_cpi_records(records: List[Dict[str, Any]], db_path: str = DB_PATH) -> int:
    """Inserts or replaces parsed CPI records into cpi_benchmarks."""
    if not records:
        return 0
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        inserted = 0
        now_str = datetime.now().isoformat()

        for r in records:
            idx_val = r.get("index") or r.get("cpi_index")
            try:
                cpi_float = float(idx_val)
            except (ValueError, TypeError):
                continue

            inf_val = r.get("inflation")
            try:
                inf_float = float(inf_val) if inf_val is not None else None
            except (ValueError, TypeError):
                inf_float = None

            yr_val = r.get("year", 2025)
            try:
                yr_int = int(yr_val)
            except (ValueError, TypeError):
                yr_int = 2025

            cursor.execute("""
            INSERT OR REPLACE INTO cpi_benchmarks (
                base_year, series, year, month, state, sector, division,
                group_name, sub_class, item_name, item_code, cpi_index,
                inflation, imputation, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                str(r.get("base_year", r.get("baseyear", "2024"))),
                str(r.get("series", "Current")),
                yr_int,
                str(r.get("month", "")),
                str(r.get("state", "All India")),
                str(r.get("sector", "Combined")),
                r.get("division"),
                r.get("group") or r.get("group_name"),
                r.get("sub_class") or r.get("subgroup"),
                r.get("item") or r.get("item_name") or "Airfare",
                str(r.get("code", r.get("item_code", "294"))),
                cpi_float,
                inf_float,
                r.get("imputation") or r.get("status"),
                now_str
            ))
            inserted += 1

        conn.commit()
        return inserted
    finally:
        conn.close()


def get_cpi_benchmarks(
    item_name: Optional[str] = None,
    state: Optional[str] = None,
    sector: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 100,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """Queries stored CPI benchmark records with filters."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = "SELECT * FROM cpi_benchmarks WHERE 1=1"
    params: List[Any] = []

    if item_name:
        query += " AND (item_name LIKE ? OR division LIKE ? OR group_name LIKE ?)"
        params.extend([f"%{item_name}%", f"%{item_name}%", f"%{item_name}%"])
    if state:
        query += " AND state = ?"
        params.append(state)
    if sector:
        query += " AND sector = ?"
        params.append(sector)
    if year:
        query += " AND year = ?"
        params.append(year)

    query += " ORDER BY year DESC, month DESC, state ASC LIMIT ?"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ingestion_logs(limit: int = 50, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves recent ingestion audit log entries."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingestion_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_index_record(record: Dict[str, Any], db_path: str = DB_PATH) -> int:
    """Inserts a calculated index record."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO index_values (
            calculation_date, base_date, frequency, jevons_index,
            naive_index, inflation_mom, match_rate_pct, matched_items_count,
            base_items_count, target_items_count, route_breakdown_json, created_at
        ) VALUES (
            :calculation_date, :base_date, :frequency, :jevons_index,
            :naive_index, :inflation_mom, :match_rate_pct, :matched_items_count,
            :base_items_count, :target_items_count, :route_breakdown_json, :created_at
        );
        """, {
            "calculation_date": record.get("calculation_date", ""),
            "base_date": record.get("base_date", ""),
            "frequency": record.get("frequency", "Daily"),
            "jevons_index": float(record.get("jevons_index", 100.0)),
            "naive_index": float(record.get("naive_index", 100.0)),
            "inflation_mom": float(record.get("inflation_mom", 0.0)),
            "match_rate_pct": float(record.get("match_rate_pct", 100.0)),
            "matched_items_count": int(record.get("matched_items_count", 0)),
            "base_items_count": int(record.get("base_items_count", 0)),
            "target_items_count": int(record.get("target_items_count", 0)),
            "route_breakdown_json": record.get("route_breakdown_json", "{}"),
            "created_at": datetime.now().isoformat()
        })
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_index_records(limit: int = 100, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves calculated index records sorted chronologically."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM index_values ORDER BY calculation_date ASC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

