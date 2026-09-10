"""
tests/test_scheduler.py
Tests: job order, failure logging, schedule-status DB reads, trigger_type tagging.
All APScheduler calls are mocked to avoid actual time-based execution.
"""
import sys, os, sqlite3, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from unittest.mock import patch, MagicMock
from scheduler import (
    _ensure_scheduler_table, _update_scheduler_state,
    get_scheduler_status, run_full_cycle
)


@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test_sched.db")
    _ensure_scheduler_table(db_path)
    return db_path


class TestSchedulerTableSetup:
    def test_scheduler_runs_table_created(self, temp_db):
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduler_runs'")
        assert cur.fetchone() is not None
        conn.close()

    def test_trigger_type_column_added_to_ingestion_logs(self, tmp_path):
        """trigger_type should be added to ingestion_logs when it already exists in the DB."""
        test_db = str(tmp_path / "test_mig.db")
        conn = sqlite3.connect(test_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                operation TEXT,
                status TEXT,
                records_ingested INTEGER,
                details_json TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Now _ensure_scheduler_table should add trigger_type via ALTER TABLE
        _ensure_scheduler_table(test_db)

        conn = sqlite3.connect(test_db)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(ingestion_logs)")
        cols = [row[1] for row in cur.fetchall()]
        conn.close()
        assert "trigger_type" in cols


class TestSchedulerStateUpdates:
    def test_update_creates_initial_row(self, temp_db):
        _update_scheduler_state("idle", "2026-09-10T03:00:00", "2026-09-11T03:00:00",
                                 None, temp_db)
        status = get_scheduler_status(temp_db)
        assert status["status"] == "idle"
        assert status["last_run_at"] == "2026-09-10T03:00:00"

    def test_update_overwrites_existing_row(self, temp_db):
        _update_scheduler_state("idle", "2026-09-10T03:00:00", None, None, temp_db)
        _update_scheduler_state("running", "2026-09-10T03:01:00", None, None, temp_db)
        status = get_scheduler_status(temp_db)
        assert status["status"] == "running"

    def test_not_started_status_when_no_rows(self, temp_db):
        status = get_scheduler_status(temp_db)
        assert status["status"] == "not_started"


class TestRunFullCycle:
    def test_cycle_returns_expected_structure(self, temp_db, tmp_path):
        """run_full_cycle should always return a dict with 'stages', 'started_at', 'completed_at'."""
        with patch("scheduler.scrape_all_routes_and_horizons", return_value=[{"status": "SAVED"}]), \
             patch("scheduler.scrape_ota_basket", return_value=[]), \
             patch("processor.run_pipeline", return_value={}):
            result = run_full_cycle(trigger_type="scheduled", db_path=temp_db, dumps_dir=str(tmp_path))
        assert "stages" in result, "Result must contain 'stages'"
        assert "started_at" in result, "Result must contain 'started_at'"
        assert "completed_at" in result, "Result must contain 'completed_at'"

    def test_cycle_stage_carrier_scrape_present(self, temp_db, tmp_path):
        """carrier_scrape stage must always be present in the cycle result."""
        with patch("scheduler.scrape_all_routes_and_horizons", return_value=[{"status": "SAVED"}]), \
             patch("scheduler.scrape_ota_basket", return_value=[]), \
             patch("processor.run_pipeline", return_value={}):
            result = run_full_cycle(trigger_type="scheduled", db_path=temp_db, dumps_dir=str(tmp_path))
        assert "carrier_scrape" in result["stages"], "carrier_scrape stage must be present"
        assert "status" in result["stages"]["carrier_scrape"], "Stage must have a status key"

    def test_trigger_type_manual_is_accepted(self, temp_db, tmp_path):
        """trigger_type='manual' should be reflected in the result."""
        with patch("scheduler.scrape_all_routes_and_horizons", return_value=[{"status": "SAVED"}]), \
             patch("scheduler.scrape_ota_basket", return_value=[]), \
             patch("processor.run_pipeline", return_value={}):
            result = run_full_cycle(trigger_type="manual", db_path=temp_db, dumps_dir=str(tmp_path))
        assert result["trigger_type"] == "manual"

    def test_cycle_all_three_stages_present(self, temp_db, tmp_path):
        """All three stages (carrier_scrape, ota_scrape, parse_dumps) must appear."""
        with patch("scheduler.scrape_all_routes_and_horizons", return_value=[{"status": "SAVED"}]), \
             patch("scheduler.scrape_ota_basket", return_value=[]), \
             patch("processor.run_pipeline", return_value={}):
            result = run_full_cycle(trigger_type="manual", db_path=temp_db, dumps_dir=str(tmp_path))
        stages = result["stages"]
        assert "carrier_scrape" in stages
        assert "ota_scrape" in stages
        assert "parse_dumps" in stages

    def test_cycle_failure_does_not_skip_other_stages(self, temp_db, tmp_path):
        """A failure in carrier_scrape should still attempt ota_scrape."""
        with patch("scheduler.scrape_all_routes_and_horizons", side_effect=RuntimeError("network error")), \
             patch("scheduler.scrape_ota_basket", return_value=[{"status": "SAVED"}]), \
             patch("processor.run_pipeline", return_value={}):
            result = run_full_cycle(trigger_type="scheduled", db_path=temp_db, dumps_dir=str(tmp_path))
        assert result["stages"]["carrier_scrape"]["status"] == "error"
        assert result["stages"]["ota_scrape"]["status"] == "ok"


