"""
tests/test_deduplication.py
Tests: exact duplicate detection, legitimate price-change not flagged,
       boundary behavior at time-window edge.
"""
import sys, os, sqlite3, tempfile
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import pandas as pd
from processor import deduplicate_quotes, DEDUP_WINDOW_MINUTES


def _create_test_db(db_path: str) -> None:
    """Create a minimal flight_quotes table for dedup testing."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flight_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin_sector TEXT,
            destination_sector TEXT,
            airline TEXT,
            flight_number TEXT,
            departure_timestamp TEXT,
            total_fare REAL,
            ingestion_timestamp TEXT,
            seat_status TEXT DEFAULT 'available',
            base_fare REAL DEFAULT 0,
            taxes REAL DEFAULT 0,
            user_development_fee REAL DEFAULT 0,
            convenience_charge REAL DEFAULT 0,
            is_math_valid INTEGER DEFAULT 1,
            is_price_outlier INTEGER DEFAULT 0,
            is_duplicate INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def _insert_existing_row(db_path: str, origin: str, dest: str, airline: str,
                          flight_num: str, dep_ts: str, total_fare: float,
                          ingestion_ts: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO flight_quotes
        (origin_sector, destination_sector, airline, flight_number,
         departure_timestamp, total_fare, ingestion_timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (origin, dest, airline, flight_num, dep_ts, total_fare, ingestion_ts))
    conn.commit()
    conn.close()


@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "dedup_test.db")
    _create_test_db(db_path)
    return db_path


class TestExactDuplicateDetection:
    def test_exact_duplicate_within_window_is_flagged(self, temp_db):
        """A quote re-scraped within 5 minutes with same key fields is a duplicate."""
        recent_ts = (datetime.now() - timedelta(minutes=2)).isoformat()  # 2min ago = within window
        _insert_existing_row(
            temp_db, "DEL", "BOM", "IndiGo", "6E-324",
            "2026-09-20T07:15:00", 6250.0, recent_ts
        )
        df = pd.DataFrame([{
            "origin_sector": "DEL",
            "destination_sector": "BOM",
            "airline": "IndiGo",
            "flight_number": "6E-324",
            "departure_timestamp": "2026-09-20T07:15:00",
            "total_fare": 6250.0,
        }])
        result = deduplicate_quotes(df, temp_db)
        assert result["is_duplicate"].iloc[0] == True, "Should be flagged as duplicate"

    def test_unique_quote_not_flagged(self, temp_db):
        """A quote that doesn't match any existing row is NOT a duplicate."""
        df = pd.DataFrame([{
            "origin_sector": "DEL",
            "destination_sector": "BLR",
            "airline": "SpiceJet",
            "flight_number": "SG-476",
            "departure_timestamp": "2026-09-21T09:00:00",
            "total_fare": 7500.0,
        }])
        result = deduplicate_quotes(df, temp_db)
        assert result["is_duplicate"].iloc[0] == False


class TestLegitimatepriceChange:
    def test_same_flight_different_price_is_not_duplicate(self, temp_db):
        """The same flight on the same date at a different price IS a new observation."""
        recent_ts = (datetime.now() - timedelta(minutes=3)).isoformat()
        _insert_existing_row(
            temp_db, "BOM", "BLR", "Air India", "AI-805",
            "2026-09-22T11:00:00", 8000.0, recent_ts
        )
        df = pd.DataFrame([{
            "origin_sector": "BOM",
            "destination_sector": "BLR",
            "airline": "Air India",
            "flight_number": "AI-805",
            "departure_timestamp": "2026-09-22T11:00:00",
            "total_fare": 8500.0,  # price CHANGED — not a duplicate
        }])
        result = deduplicate_quotes(df, temp_db)
        assert result["is_duplicate"].iloc[0] == False, \
            "Price change should not be flagged as duplicate"


class TestTimeWindowBoundary:
    def test_outside_window_is_not_duplicate(self, temp_db):
        """A quote older than DEDUP_WINDOW_MINUTES is NOT a duplicate — it's historical."""
        old_ts = (datetime.now() - timedelta(minutes=DEDUP_WINDOW_MINUTES + 2)).isoformat()
        _insert_existing_row(
            temp_db, "MAA", "DEL", "Akasa Air", "QP-1302",
            "2026-09-23T14:30:00", 7200.0, old_ts
        )
        df = pd.DataFrame([{
            "origin_sector": "MAA",
            "destination_sector": "DEL",
            "airline": "Akasa Air",
            "flight_number": "QP-1302",
            "departure_timestamp": "2026-09-23T14:30:00",
            "total_fare": 7200.0,
        }])
        result = deduplicate_quotes(df, temp_db)
        assert result["is_duplicate"].iloc[0] == False, \
            "Quote outside the time window should NOT be flagged as duplicate"

    def test_is_duplicate_column_always_present(self, temp_db):
        """deduplicate_quotes must always add is_duplicate column even with empty df."""
        df = pd.DataFrame(columns=["origin_sector", "destination_sector", "airline",
                                    "flight_number", "departure_timestamp", "total_fare"])
        result = deduplicate_quotes(df, temp_db)
        assert "is_duplicate" in result.columns
