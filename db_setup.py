# =============================================================================
# db_setup.py
# =============================================================================
# Purpose : Create (or validate) the `flight_quotes.db` SQLite database and
#           its primary table.  Safe to re-run — uses CREATE TABLE IF NOT
#           EXISTS so it will never wipe existing data.
#
# Run ONCE before processor.py:
#   python db_setup.py
# =============================================================================

import sqlite3
import os
import sys


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DB_NAME = "flight_quotes.db"


def get_db_path() -> str:
    """Return absolute path to the database, co-located with this script."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)




def _safe_add_columns(cursor, table: str, columns: list) -> None:
    """
    Safely add columns to an existing SQLite table using ALTER TABLE.
    Silently ignores 'duplicate column' errors so this is safe to re-run
    on already-migrated databases without losing data.
    """
    for col_name, col_def in columns:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass  # Column already exists — safe to ignore


def init_db(db_path: str | None = None) -> str:
    """
    Create the `flight_quotes` table if it doesn't already exist.

    Parameters
    ----------
    db_path : str, optional
        Absolute path to the SQLite file.  Defaults to `get_db_path()`.

    Returns
    -------
    str
        The path to the (now-initialised) database file.
    """
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # -------------------------------------------------------------------------
    # Primary data table
    # Two extra boolean columns are added by the pipeline (not by Gemini):
    #   is_math_valid    → True when base+taxes+udf+cc == total (within 0.01)
    #   is_price_outlier → True when |z-score| > 3 across the ingestion batch
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flight_quotes (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Core flight identifiers
            flight_number        TEXT    NOT NULL,
            airline              TEXT    NOT NULL,
            origin_sector        TEXT    NOT NULL,
            destination_sector   TEXT    NOT NULL,
            departure_timestamp  TEXT    NOT NULL,

            -- Fare breakdown (all amounts in INR)
            base_fare            REAL    NOT NULL,
            taxes                REAL    NOT NULL,
            user_development_fee REAL    NOT NULL,
            convenience_charge   REAL    NOT NULL,
            total_fare           REAL    NOT NULL,

            -- Seat availability
            seat_status          TEXT    NOT NULL
                CHECK (seat_status IN ('available', 'sold-out', 'cancelled')),

            -- Pipeline-computed quality flags
            is_math_valid        INTEGER NOT NULL DEFAULT 1,   -- BOOLEAN (0/1)
            is_price_outlier     INTEGER NOT NULL DEFAULT 0,   -- BOOLEAN (0/1)
            is_duplicate         INTEGER NOT NULL DEFAULT 0,   -- BOOLEAN (0/1)

            -- Source metadata
            source_type          TEXT    DEFAULT 'aggregator',
            ota_platform         TEXT,
            fare_class           TEXT    DEFAULT 'UNKNOWN',

            -- Audit
            source_file          TEXT,
            ingestion_timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Safe ALTER TABLE migrations for existing databases (SQLite ignores duplicate cols)
    _safe_add_columns(cursor, "flight_quotes", [
        ("is_duplicate",  "INTEGER NOT NULL DEFAULT 0"),
        ("source_type",   "TEXT DEFAULT 'aggregator'"),
        ("ota_platform",  "TEXT"),
        ("fare_class",    "TEXT DEFAULT 'UNKNOWN'"),
    ])

    conn.commit()
    conn.close()

    print(f"[db_setup] Database ready -> {db_path}")
    return db_path


# ---------------------------------------------------------------------------
# Stand-alone entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    path = init_db()
    print(f"[db_setup] Table 'flight_quotes' created/verified at: {path}")
    sys.exit(0)
