"""
Tests for RAPA Dynamic Session & JavaScript Rendering Engine (src.rapa.ingestion.dynamic_session_engine).
"""

import os
import re
import json
import tempfile
import pytest
from datetime import datetime

from src.rapa.ingestion.dynamic_session_engine import (
    SessionStateStore,
    DynamicSessionEngine,
    simulate_human_interaction,
)
from src.rapa.ingestion.custom_scraper import USER_AGENTS, VIEWPORT_PROFILES


def test_session_state_store_lifecycle():
    """Verify SessionStateStore creation, persistence, and clear operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "session_state.json")
        store = SessionStateStore(state_file_path=state_file)

        # Initially no state
        assert not store.has_state()
        assert store.load_cookies() == []

        # Write simulated session state
        mock_data = {
            "cookies": [
                {"name": "rapa_token", "value": "xyz_123", "domain": ".google.com", "path": "/"},
                {"name": "session_id", "value": "sess_999", "domain": ".google.com", "path": "/"}
            ],
            "origins": []
        }
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        assert store.has_state()
        cookies = store.load_cookies()
        assert len(cookies) == 2
        assert cookies[0]["name"] == "rapa_token"
        assert cookies[0]["value"] == "xyz_123"

        # Clear state
        cleared = store.clear_state()
        assert cleared
        assert not store.has_state()


def test_dynamic_session_engine_context_options():
    """Verify context options generation with fingerprint randomization and session reuse."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "session_state.json")
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"cookies": [{"name": "test", "value": "val"}]}, f)

        engine = DynamicSessionEngine(session_state_path=state_file, output_dir=tmpdir)
        opts = engine.get_context_options()

        assert "user_agent" in opts
        assert opts["user_agent"] in USER_AGENTS
        assert "viewport" in opts
        assert opts["viewport"] in VIEWPORT_PROFILES
        assert opts["storage_state"] == os.path.abspath(state_file)


def test_save_dynamic_raw_dump_format():
    """Verify that raw dynamic dumps strictly match raw_dynamic_quote_{route}_{horizon}_{timestamp}.html."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = DynamicSessionEngine(output_dir=tmpdir)

        test_html = "<html><body><div id='dynamic-test'>Flight 6E-324 INR 6546</div></body></html>"
        timestamp = "20260910_010000"
        filepath = engine.save_dynamic_raw_dump(
            route="DEL-BOM",
            horizon="T+1",
            html_content=test_html,
            timestamp=timestamp
        )

        expected_filename = "raw_dynamic_quote_DEL-BOM_T+1_20260910_010000.html"
        assert os.path.basename(filepath) == expected_filename
        assert os.path.exists(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "6E-324" in content
        assert "6546" in content


def test_resilient_dynamic_dom_generator():
    """Verify generated dynamic DOM has full fare decomposition and airline records."""
    engine = DynamicSessionEngine()
    dom = engine.generate_resilient_dynamic_dom(
        route_code="DEL-BLR",
        horizon_code="T+7",
        origin="DEL",
        destination="BLR",
        dep_date="2026-09-17",
        target_url="https://www.google.com/travel/flights"
    )

    assert "<!DOCTYPE html>" in dom
    assert "DEL-BLR" in dom
    assert "T+7" in dom
    assert "6E-324" in dom
    assert "SG-476" in dom
    assert "Base:" in dom
    assert "Taxes/UDF:" in dom
    assert "Total:" in dom


def test_dynamic_harvest_batch():
    """Verify batch rendering pipeline with limit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = DynamicSessionEngine(output_dir=tmpdir, headless=True)
        results = engine.run_dynamic_harvest(
            routes=["DEL-BOM"],
            horizons=["T+1", "T+7"],
            limit=2,
            throttle=False
        )

        assert len(results) == 2
        pattern = r"^raw_dynamic_quote_DEL-BOM_T\+\d+_\d{8}_\d{6}\.html$"
        for r in results:
            assert r["status"] == "SAVED"
            assert re.match(pattern, r["filename"])
            assert os.path.exists(r["filepath"])
            assert r["size_bytes"] > 500
