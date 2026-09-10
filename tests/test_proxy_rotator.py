"""
tests/test_proxy_rotator.py
Tests: pool parsing, validate_pool filtering (mocked), rotation order,
loud-fail with --use-proxies + empty pool, quiet-pass without flag.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from unittest.mock import patch, MagicMock
from src.rapa.ingestion.custom_scraper import ProxyRotator, scrape_ota_basket, RAPAStealthEngine


class TestProxyPoolParsing:
    def test_parses_comma_separated_proxies(self):
        r = ProxyRotator(["http://1.2.3.4:8080", "http://5.6.7.8:3128"])
        assert len(r.proxies) == 2
        assert "http://1.2.3.4:8080" in r.proxies

    def test_strips_whitespace_from_proxy_strings(self):
        r = ProxyRotator(["  http://1.2.3.4:8080  ", "http://5.6.7.8:3128"])
        assert all(" " not in p for p in r.proxies)

    def test_empty_list_results_in_unconfigured(self):
        r = ProxyRotator([])
        assert not r.is_configured()

    def test_single_proxy_configured(self):
        r = ProxyRotator(["http://proxy.example.com:8080"])
        assert r.is_configured()


class TestProxyRotation:
    def test_round_robin_rotation(self):
        r = ProxyRotator(["http://p1:8080", "http://p2:8080", "http://p3:8080"])
        results = [r.get_proxy() for _ in range(6)]
        # Should cycle: p1, p2, p3, p1, p2, p3
        assert results[0] == results[3]
        assert results[1] == results[4]
        assert results[2] == results[5]

    def test_returns_none_with_no_proxies(self):
        r = ProxyRotator([])
        assert r.get_proxy() is None

    def test_add_proxy_expands_pool(self):
        r = ProxyRotator(["http://p1:8080"])
        r.add_proxy("http://p2:8080")
        assert len(r.proxies) == 2


class TestValidatePool:
    def test_validate_pool_keeps_live_proxies(self):
        r = ProxyRotator(["http://live-proxy:8080", "http://dead-proxy:9999"])

        def mock_urlopen(req, timeout=5):
            url_str = req.get_full_url()
            if "live" in str(req.host) or True:  # mock all as live
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.read.return_value = b'{"origin": "1.2.3.4"}'
                mock_resp.__enter__ = lambda s: s
                mock_resp.__exit__ = MagicMock(return_value=False)
                return mock_resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            results = r.validate_pool()
        assert len(results) == 2

    def test_validate_pool_removes_dead_proxies(self):
        r = ProxyRotator(["http://dead1:1111", "http://dead2:2222"])

        def mock_urlopen_raises(req, timeout=5):
            raise ConnectionRefusedError("Connection refused")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_raises):
            results = r.validate_pool()

        assert all(v is False for v in results.values())
        assert len(r.proxies) == 0, "Dead proxies should be removed from pool"


class TestLoudFailWithProxies:
    def test_scrape_ota_raises_if_use_proxies_and_no_pool(self):
        engine = RAPAStealthEngine()
        engine.proxy_rotator = ProxyRotator([])  # empty pool
        with pytest.raises(RuntimeError, match="RAPA_PROXIES is not configured"):
            scrape_ota_basket(engine=engine, limit=1, throttle=False, use_proxies=True)

    def test_scrape_ota_no_error_without_use_proxies_flag(self, tmp_path):
        from unittest.mock import patch
        with patch("src.rapa.ingestion.custom_scraper.RobotsChecker.can_fetch", return_value=True), \
             patch("src.rapa.ingestion.custom_scraper.RAPAStealthEngine.fetch_page_with_stealth", return_value=None):
            engine = RAPAStealthEngine(output_dir=str(tmp_path))
            engine.proxy_rotator = ProxyRotator([])  # empty pool
            # Should NOT raise — use_proxies=False is the default
            results = scrape_ota_basket(engine=engine, portals=["ixigo"], limit=1, throttle=False, use_proxies=False)
        assert len(results) >= 1
