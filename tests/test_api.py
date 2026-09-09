"""
API Route Integration Tests for RAPA FastAPI Service.
Covers:
- Base benchmark and health endpoints
- Custom index aggregation (Formula lab)
- Outlier governance and health matrix
- Route proximity matrix
- Multi-format report export
"""

import pytest
from fastapi.testclient import TestClient
import unittest.mock

from api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "RAPA" in response.text
    assert "Airfare Price Index" in response.text




def test_health_endpoint():
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
    assert "database" in data
    assert "modules" in data


def test_fares_status_endpoint():
    response = client.get("/v1/fares/status")
    assert response.status_code == 200
    data = response.json()
    assert "Ignav" in data["provider"]
    assert "target_basket" in data


def test_ingest_cpi_endpoint():
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
                "item": "Airfare",
                "code": "07.3.3.1.2.01",
                "index": "124.23",
                "imputation": "N"
            }
        ]
    }

    with unittest.mock.patch("esankhyiki.get_data", return_value=mock_payload):
        response = client.post("/v1/ingest/cpi?year=2025&base_year=2024")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert "airfare_ingestion" in data


def test_benchmark_airfare_endpoint():
    response = client.get("/v1/benchmark/airfare")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["data"], list)


def test_index_daily_endpoint():
    response = client.get("/v1/index/daily")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["data"], list)


def test_index_summary_endpoint():
    response = client.get("/v1/index/summary")
    assert response.status_code == 200
    data = response.json()
    assert "headline_index" in data
    assert "target_basket_weights" in data


def test_custom_aggregate_endpoint():
    payload = {
        "formula": "carli",
        "custom_weights": {"DEL-BOM": 0.5, "DEL-BLR": 0.5}
    }
    response = client.post("/v1/index/custom-aggregate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPUTED"
    assert data["formula_selected"] == "CARLI"


def test_governance_outliers_endpoint():
    response = client.get("/v1/governance/outliers")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "outliers" in data


def test_governance_health_matrix_endpoint():
    response = client.get("/v1/governance/health-matrix")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "pipeline_metrics" in data
    assert "sources" in data


def test_routes_matrix_endpoint():
    response = client.get("/v1/routes/matrix")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "airports" in data
    assert "corridors" in data
    assert "DEL-BOM" in data["corridors"]
    assert "distance_km" in data["corridors"]["DEL-BOM"]


def test_export_report_endpoint():
    response = client.get("/v1/export/report?format=csv&dataset=quotes")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")

    response_json = client.get("/v1/export/report?format=json&dataset=quotes")
    assert response_json.status_code == 200
    assert "records" in response_json.json()


def test_validation_cpi_comparison_endpoint():
    response = client.get("/v1/validation/cpi-comparison")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ACTIVE_SERIES_EVALUATION", "INITIALIZING_BASE_PERIOD", "VALIDATED")



def test_logs_endpoint():
    response = client.get("/v1/logs")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
