import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_sector_heatmaps_endpoint():
    res = client.get("/v1/heatmap/sectors")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "sector_horizon_heatmap" in data
    assert len(data["sector_horizon_heatmap"]) == 6
    assert "sector_carrier_heatmap" in data
    assert "global_price_envelope" in data

def test_dgca_30days_backtest_endpoint():
    res = client.get("/v1/validation/dgca-30days")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["evaluation_window_days"] == 30
    assert len(data["daily_time_series"]) == 30
    assert "statistical_kpis" in data
    assert data["statistical_kpis"]["pearson_correlation_r"] >= 0.90
    assert "root_mean_squared_error_pts" in data["statistical_kpis"]

def test_nso_rbi_feed_endpoint():
    res = client.get("/v1/nso-rbi/feed")
    assert res.status_code == 200
    data = res.json()
    assert "agency_target" in data
    assert "primary_index" in data
    assert "sector_sub_indices" in data
    assert len(data["sector_sub_indices"]) == 6