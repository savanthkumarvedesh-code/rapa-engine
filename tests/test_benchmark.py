"""
Unit Tests for MoSPI eSankhyiki Benchmark Ingestion Module.
"""

import os
import tempfile
import unittest.mock
import pytest

from data.db import init_db, get_connection, get_cpi_benchmarks, get_ingestion_logs
from benchmark.mospi_client import MoSPIBenchmarkClient


def test_mospi_client_discovery_mocked():
    """Verifies discovery extracts Item 294 Airfare and logs appropriately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        client = MoSPIBenchmarkClient(db_path=db_path)

        mock_meta = [{
            "item": [
                {"item_code": 294, "item_name": "Airfare", "division_code": 7},
                {"item_code": 283, "item_name": "Rail fare", "division_code": 7},
                {"item_code": 101, "item_name": "Rice", "division_code": 1}
            ]
        }]

        with unittest.mock.patch("esankhyiki.get_metadata", return_value=mock_meta):
            res = client.discover_cpi_metadata(base_year="2024", level="Item")

        assert res["status"] == "success"
        assert res["total_items_count"] == 3
        assert len(res["transport_items"]) == 2

        # Check that audit log was created
        logs = get_ingestion_logs(db_path=db_path)
        assert len(logs) == 1
        assert logs[0]["status"] == "SUCCESS"
        assert logs[0]["operation"] == "discover_cpi_metadata"


def test_mospi_client_ingest_airfare():
    """Verifies CPI Item 294 ingestion saves rows into cpi_benchmarks and records audit log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        client = MoSPIBenchmarkClient(db_path=db_path)

        mock_payload = {
            "data": [
                {
                    "base_year": "2024",
                    "series": "Current",
                    "year": "2025",
                    "month": "December",
                    "state": "All India",
                    "sector": "Combined",
                    "division": "Transport",
                    "group": "Passenger transport services",
                    "class": "Passenger transport by air",
                    "sub_class": "Passenger transport by air, domestic",
                    "item": "Airfare",
                    "code": "07.3.3.1.2.01",
                    "index": "124.23",
                    "inflation": "6.5",
                    "imputation": "N"
                },
                {
                    "base_year": "2024",
                    "series": "Current",
                    "year": "2025",
                    "month": "December",
                    "state": "Delhi",
                    "sector": "Urban",
                    "division": "Transport",
                    "group": "Passenger transport services",
                    "class": "Passenger transport by air",
                    "sub_class": "Passenger transport by air, domestic",
                    "item": "Airfare",
                    "code": "07.3.3.1.2.01",
                    "index": "131.50",
                    "inflation": "7.2",
                    "imputation": "N"
                }
            ],
            "meta_data": {"page": 1, "totalRecords": 2}
        }

        with unittest.mock.patch("esankhyiki.get_data", return_value=mock_payload):
            res = client.fetch_cpi_airfare_data(year="2025", base_year="2024")

        assert res["status"] == "success"
        assert res["records_saved"] == 2

        # Verify queryable from DB
        records = get_cpi_benchmarks(item_name="Airfare", db_path=db_path)
        assert len(records) == 2
        assert records[0]["cpi_index"] in (124.23, 131.50)

        # Verify audit logs
        logs = get_ingestion_logs(db_path=db_path)
        assert len(logs) == 1
        assert logs[0]["status"] == "SUCCESS"
        assert logs[0]["records_ingested"] == 2
