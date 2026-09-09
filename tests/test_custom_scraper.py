"""
Tests for RAPA Custom Stealth Scraper Module (src.rapa.ingestion.custom_scraper).
"""

import os
import re
import pytest
import tempfile
from datetime import datetime

from src.rapa.ingestion.custom_scraper import (
    ProxyRotator,
    RobotsChecker,
    human_delay,
    RAPAStealthEngine,
    scrape_all_routes_and_horizons,
    TRUNK_ROUTES,
    BOOKING_HORIZONS,
    USER_AGENTS,
    VIEWPORT_PROFILES,
)


def test_trunk_routes_and_horizons_definitions():
    """Verify that all 6 DGCA trunk routes and 5 horizons are accurately defined."""
    assert len(TRUNK_ROUTES) == 6
    route_codes = [r["code"] for r in TRUNK_ROUTES]
    assert "DEL-BOM" in route_codes
    assert "DEL-BLR" in route_codes
    assert "BOM-BLR" in route_codes
    assert "DEL-CCU" in route_codes
    assert "BLR-HYD" in route_codes
    assert "MAA-DEL" in route_codes

    assert len(BOOKING_HORIZONS) == 5
    horizon_codes = [h["code"] for h in BOOKING_HORIZONS]
    assert horizon_codes == ["T+1", "T+7", "T+15", "T+30", "T+45"]


def test_proxy_rotator_behavior():
    """Verify ProxyRotator round-robin rotation and fallback."""
    # Empty rotator
    empty_rotator = ProxyRotator(proxies=[])
    assert empty_rotator.get_proxy() is None
    assert not empty_rotator.is_configured()

    # Configured rotator
    proxies = ["http://proxy1:8080", "http://proxy2:8080", "socks5://127.0.0.1:9050"]
    rotator = ProxyRotator(proxies=proxies)
    assert rotator.is_configured()

    # Round-robin cycle
    p1 = rotator.get_proxy()
    p2 = rotator.get_proxy()
    p3 = rotator.get_proxy()
    p4 = rotator.get_proxy()

    assert p1 == "http://proxy1:8080"
    assert p2 == "http://proxy2:8080"
    assert p3 == "socks5://127.0.0.1:9050"
    assert p4 == "http://proxy1:8080"  # Wrapped around


def test_fingerprint_randomization():
    """Verify User-Agent and Viewport randomized fingerprint generation."""
    engine = RAPAStealthEngine()
    fp = engine.get_random_fingerprint()

    assert "useragent" in fp
    assert "viewport" in fp
    assert fp["useragent"] in USER_AGENTS
    assert fp["viewport"] in VIEWPORT_PROFILES


def test_robots_checker_safeguards():
    """Verify RobotsChecker RFC 9309 check and domain caching."""
    checker = RobotsChecker()
    # Testing permission check on a standard public URL
    can_fetch = checker.can_fetch("https://example.com/test", user_agent="*")
    assert isinstance(can_fetch, bool)


def test_human_delay_jitter():
    """Verify human_delay pacing with randomized jitter."""
    # Fast test
    t0 = datetime.now()
    d = human_delay(min_s=0.05, max_s=0.1, enabled=True)
    t1 = datetime.now()
    elapsed = (t1 - t0).total_seconds()
    assert 0.04 <= elapsed <= 0.3
    assert 0.05 <= d <= 0.1

    # Disabled test
    d_off = human_delay(min_s=1.0, max_s=2.0, enabled=False)
    assert d_off == 0.0


def test_stealth_engine_raw_dump_generation_and_naming():
    """Verify that raw dumps are created automatically with strict quote_{route}_{horizon}_{timestamp}.html naming."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = RAPAStealthEngine(output_dir=tmpdir)
        assert os.path.exists(tmpdir)

        test_html = "<html><body><div class='test-flight'>SG-476 INR 6528</div></body></html>"
        timestamp = "20260910_120000"
        filepath = engine.save_raw_dump("DEL-BOM", "T+1", test_html, timestamp=timestamp)

        expected_filename = "quote_DEL-BOM_T+1_20260910_120000.html"
        assert os.path.basename(filepath) == expected_filename
        assert os.path.exists(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            read_back = f.read()
        assert "SG-476" in read_back
        assert "6528" in read_back


def test_harvest_quote_and_batch_pipeline():
    """Verify harvesting single quote and running batch across subsets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = RAPAStealthEngine(output_dir=tmpdir)

        # Single harvest
        quote_meta = engine.harvest_quote(
            route_code="DEL-BOM",
            horizon_code="T+1",
            origin="DEL",
            destination="BOM",
            dep_date="2026-09-11",
            use_live_fetch=False  # Test resilient offline fallback
        )

        assert quote_meta["status"] == "SAVED"
        assert os.path.exists(quote_meta["filepath"])
        assert quote_meta["size_bytes"] > 500

        # Pattern check
        pattern = r"^quote_DEL-BOM_T\+1_\d{8}_\d{6}\.html$"
        assert re.match(pattern, quote_meta["filename"])

        # Batch runner with limit
        results = scrape_all_routes_and_horizons(
            engine=engine,
            routes=["DEL-BOM", "DEL-BLR"],
            horizons=["T+1"],
            throttle=False,
            limit=2
        )
        assert len(results) == 2
        for res in results:
            assert res["status"] == "SAVED"
            assert os.path.exists(res["filepath"])
