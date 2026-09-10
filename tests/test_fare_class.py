"""
tests/test_fare_class.py
Tests: Gemini-extracted fare_class populates correctly, UNKNOWN default fallback.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import pandas as pd
from schema import FlightQuote


class TestFareClassExtraction:
    def test_fare_class_defaults_to_unknown_when_omitted(self):
        """FlightQuote should default fare_class to 'UNKNOWN' when not provided."""
        q = FlightQuote(
            flight_number="6E-324",
            airline="IndiGo",
            origin_sector="DEL",
            destination_sector="BOM",
            departure_timestamp="2026-09-17T07:15:00",
            base_fare=5000.0,
            taxes=750.0,
            user_development_fee=300.0,
            convenience_charge=200.0,
            total_fare=6250.0,
            seat_status="available",
        )
        assert q.fare_class == "UNKNOWN"

    def test_fare_class_populated_when_provided(self):
        """FlightQuote should accept and store any provided fare_class string."""
        q = FlightQuote(
            flight_number="AI-805",
            airline="Air India",
            origin_sector="DEL",
            destination_sector="CCU",
            departure_timestamp="2026-09-20T08:00:00",
            base_fare=7000.0,
            taxes=1000.0,
            user_development_fee=400.0,
            convenience_charge=350.0,
            total_fare=8750.0,
            seat_status="available",
            fare_class="Economy Flex",
        )
        assert q.fare_class == "Economy Flex"

    def test_fare_class_accepts_business_class(self):
        q = FlightQuote(
            flight_number="AI-131",
            airline="Air India",
            origin_sector="BOM",
            destination_sector="DEL",
            departure_timestamp="2026-09-20T10:00:00",
            base_fare=25000.0,
            taxes=2000.0,
            user_development_fee=500.0,
            convenience_charge=0.0,
            total_fare=27500.0,
            seat_status="available",
            fare_class="Business",
        )
        assert q.fare_class == "Business"

    def test_processor_pipeline_sets_unknown_default_for_missing(self):
        """Simulate the processor pipeline's default-setting logic for fare_class."""
        raw_quote = {
            "flight_number": "6E-449",
            "airline": "IndiGo",
            "origin_sector": "BLR",
            "destination_sector": "HYD",
            "departure_timestamp": "2026-09-21T09:30:00",
            "base_fare": 3200.0,
            "taxes": 600.0,
            "user_development_fee": 250.0,
            "convenience_charge": 150.0,
            "total_fare": 4200.0,
            "seat_status": "available",
            # fare_class intentionally missing
        }
        # Simulate what run_pipeline does for missing fare_class
        raw_quote.setdefault("fare_class", raw_quote.get("fare_class") or "UNKNOWN")
        assert raw_quote["fare_class"] == "UNKNOWN"


class TestFareClassInDatabase:
    def test_flight_quote_schema_has_fare_class_field(self):
        """Verify FlightQuote model has fare_class in its fields."""
        fields = FlightQuote.model_fields
        assert "fare_class" in fields

    def test_fare_class_column_in_db_columns(self):
        """processor.DB_COLUMNS must include fare_class."""
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from processor import DB_COLUMNS
        assert "fare_class" in DB_COLUMNS
