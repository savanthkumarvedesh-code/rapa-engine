"""
tests/test_ota_scraper.py
Tests: URL construction, dump filename format, source_type tagging, mocked end-to-end cycle.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from src.rapa.ingestion.custom_scraper import (
    build_ota_query_url, OTA_PORTALS, generate_ota_raw_dump,
    scrape_ota_basket, RAPAStealthEngine, ProxyRotator
)


class TestOTAURLConstruction:
    def test_makemytrip_url_format(self):
        url = build_ota_query_url("makemytrip", "DEL", "BOM", "2026-09-20")
        assert "makemytrip.com" in url
        assert "DEL" in url
        assert "BOM" in url
        assert "20260920" in url  # date-nodash format
        assert "tripType=O" in url  # MMT-specific one-way param

    def test_ixigo_url_format(self):
        url = build_ota_query_url("ixigo", "BLR", "HYD", "2026-10-01")
        assert "ixigo.com" in url
        assert "BLR" in url
        assert "HYD" in url
        assert "2026-10-01" in url  # Ixigo uses YYYY-MM-DD

    def test_cleartrip_url_format(self):
        url = build_ota_query_url("cleartrip", "DEL", "CCU", "2026-09-25")
        assert "cleartrip.com" in url
        assert "DEL" in url and "CCU" in url
        assert "depart_date=2026-09-25" in url

    def test_all_six_portals_build_url(self):
        for portal in OTA_PORTALS.keys():
            url = build_ota_query_url(portal, "MAA", "DEL", "2026-09-30")
            assert url.startswith("https://"), f"Portal {portal} URL does not start with https"
            assert "MAA" in url or portal == "easemytrip", f"Portal {portal} URL missing origin"

    def test_unknown_portal_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown OTA portal"):
            build_ota_query_url("nonexistent", "DEL", "BOM", "2026-09-20")


class TestOTADumpFilename:
    def test_filename_prefix_is_ota_quote(self, tmp_path):
        from unittest.mock import patch
        with patch("src.rapa.ingestion.custom_scraper.RobotsChecker.can_fetch", return_value=True), \
             patch("src.rapa.ingestion.custom_scraper.RAPAStealthEngine.fetch_page_with_stealth", return_value=None):
            engine = RAPAStealthEngine(output_dir=str(tmp_path))
            results = scrape_ota_basket(engine=engine, portals=["makemytrip"], limit=1, throttle=False)
        assert results, "Expected at least one OTA dump"
        filename = results[0]["filename"]
        assert filename.startswith("ota_quote_"), f"Filename should start with 'ota_quote_': {filename}"

    def test_filename_contains_portal_name(self, tmp_path):
        from unittest.mock import patch
        with patch("src.rapa.ingestion.custom_scraper.RobotsChecker.can_fetch", return_value=True), \
             patch("src.rapa.ingestion.custom_scraper.RAPAStealthEngine.fetch_page_with_stealth", return_value=None):
            engine = RAPAStealthEngine(output_dir=str(tmp_path))
            results = scrape_ota_basket(engine=engine, portals=["goibibo"], limit=1, throttle=False)
        filename = results[0]["filename"]
        assert "goibibo" in filename, f"Portal name missing from filename: {filename}"

    def test_dump_file_written_to_disk(self, tmp_path):
        from unittest.mock import patch
        with patch("src.rapa.ingestion.custom_scraper.RobotsChecker.can_fetch", return_value=True), \
             patch("src.rapa.ingestion.custom_scraper.RAPAStealthEngine.fetch_page_with_stealth", return_value=None):
            engine = RAPAStealthEngine(output_dir=str(tmp_path))
            results = scrape_ota_basket(engine=engine, portals=["ixigo"], limit=1, throttle=False)
        filepath = results[0]["filepath"]
        assert os.path.exists(filepath), f"OTA dump file not found: {filepath}"
        assert os.path.getsize(filepath) > 100, "OTA dump too small — content not written"


class TestOTASourceTypeTagging:
    def test_result_metadata_source_type_is_ota(self, tmp_path):
        from unittest.mock import patch
        with patch("src.rapa.ingestion.custom_scraper.RobotsChecker.can_fetch", return_value=True), \
             patch("src.rapa.ingestion.custom_scraper.RAPAStealthEngine.fetch_page_with_stealth", return_value=None):
            engine = RAPAStealthEngine(output_dir=str(tmp_path))
            results = scrape_ota_basket(engine=engine, portals=["cleartrip"], limit=1, throttle=False)
        assert results[0]["source_type"] == "ota"

    def test_result_metadata_has_portal_display(self, tmp_path):
        from unittest.mock import patch
        with patch("src.rapa.ingestion.custom_scraper.RobotsChecker.can_fetch", return_value=True), \
             patch("src.rapa.ingestion.custom_scraper.RAPAStealthEngine.fetch_page_with_stealth", return_value=None):
            engine = RAPAStealthEngine(output_dir=str(tmp_path))
            results = scrape_ota_basket(engine=engine, portals=["yatra"], limit=1, throttle=False)
        assert results[0]["portal_display"] == "Yatra"


class TestOTARawDumpContent:
    def test_ota_dump_html_contains_portal_metadata(self):
        html = generate_ota_raw_dump(
            "easemytrip", "DEL-BOM", "T+7", "DEL", "BOM", "2026-09-20",
            "https://flights.easemytrip.com/test"
        )
        assert 'source-type" content="ota"' in html
        assert 'ota-portal" content="easemytrip"' in html
        assert "DEL" in html and "BOM" in html

    def test_ota_dump_html_contains_fare_class(self):
        html = generate_ota_raw_dump(
            "makemytrip", "DEL-BLR", "T+15", "DEL", "BLR", "2026-10-01",
            "https://www.makemytrip.com/test"
        )
        assert "Economy" in html, "OTA dump should include fare class info"
