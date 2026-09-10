"""
scheduler.py
============
RAPA Engine — APScheduler-based daily extraction scheduler.

This is a functional prototype scheduler consistent with the SIH prototype-stage
expectation. It orchestrates the existing scrape -> scrape-ota -> parse-dumps
pipeline on a configurable cron schedule WITHOUT bypassing any existing
safeguards (robots.txt, human_delay, rate-limiting).

Usage:
  python run.py schedule-start      # Launch scheduler (long-running)
  python run.py schedule-status     # Print last/next run from DB
  python run.py schedule-trigger    # Trigger one immediate full cycle
"""

import logging
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Try APScheduler; degrade gracefully with helpful message if missing
# ---------------------------------------------------------------------------
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

from data.db import DB_PATH, get_connection, log_ingestion, init_db
from src.rapa.ingestion.custom_scraper import (
    RAPAStealthEngine,
    ProxyRotator,
    scrape_all_routes_and_horizons,
    scrape_ota_basket,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [RAPA-SCHEDULER] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rapa.scheduler")

# Default cron: 03:00 IST = 21:30 UTC previous day
DEFAULT_CRON = os.getenv("RAPA_SCHEDULE_CRON", "30 21 * * *")
SCHEDULER_STATE_TABLE = "scheduler_runs"


def _ensure_scheduler_table(db_path: str = DB_PATH) -> None:
    """Create scheduler_runs table and trigger_type column in ingestion_logs if not already present."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            last_run_at TEXT,
            next_run_at TEXT,
            status      TEXT NOT NULL DEFAULT 'idle',
            cycle_result TEXT,
            updated_at  TEXT NOT NULL
        )
    """)
    # Add trigger_type to ingestion_logs if missing (backfill existing rows as 'manual')
    try:
        cur.execute("ALTER TABLE ingestion_logs ADD COLUMN trigger_type TEXT DEFAULT 'manual'")
        # Backfill existing rows
        cur.execute("UPDATE ingestion_logs SET trigger_type = 'manual' WHERE trigger_type IS NULL")
    except Exception:
        pass  # Column already exists
    conn.commit()
    conn.close()


def _update_scheduler_state(status: str, last_run: Optional[str], next_run: Optional[str],
                             cycle_result: Optional[str] = None, db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    # Upsert single-row state
    cur.execute("SELECT id FROM scheduler_runs ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE scheduler_runs SET last_run_at=?, next_run_at=?, status=?, cycle_result=?, updated_at=? WHERE id=?",
            (last_run, next_run, status, cycle_result, now, row[0])
        )
    else:
        cur.execute(
            "INSERT INTO scheduler_runs (last_run_at, next_run_at, status, cycle_result, updated_at) VALUES (?,?,?,?,?)",
            (last_run, next_run, status, cycle_result, now)
        )
    conn.commit()
    conn.close()


def run_full_cycle(trigger_type: str = "scheduled", db_path: str = DB_PATH, dumps_dir: str = "./raw_dumps") -> dict:
    """
    Executes one full extraction cycle:
      1. scrape  (RAPAStealthEngine carrier portals)
      2. scrape-ota (6 OTA portals)
      3. parse-dumps (Gemini AI extraction + data quality gates)

    All existing safeguards (robots.txt, human_delay, rate-limiting,
    math validation, Z-score outlier detection, deduplication) are
    applied exactly as in manual invocation — the scheduler does NOT
    bypass any of them.

    Parameters
    ----------
    trigger_type : str
        'scheduled' or 'manual'. Logged to ingestion_logs.trigger_type.
    db_path : str
        Target SQLite database path.
    dumps_dir : str
        Directory to write and parse raw HTML dumps.

    Returns
    -------
    dict
        Cycle result summary.
    """
    _ensure_scheduler_table(db_path)
    logger.info("[CYCLE] Starting full extraction cycle (trigger_type=%s)...", trigger_type)
    result = {"trigger_type": trigger_type, "started_at": datetime.now().isoformat(), "stages": {}}

    rotator = ProxyRotator()
    engine = RAPAStealthEngine(proxy_rotator=rotator, output_dir=dumps_dir)

    # Stage 1 — Carrier scrape
    try:
        dumps = scrape_all_routes_and_horizons(engine=engine, limit=6, throttle=True)
        result["stages"]["carrier_scrape"] = {"status": "ok", "dumps": len(dumps)}
        log_ingestion("RAPAStealthEngine", "carrier_scrape", "success", len(dumps),
                      {"trigger_type": trigger_type}, db_path)
    except Exception as e:
        logger.error("[CYCLE] Carrier scrape failed: %s", e)
        result["stages"]["carrier_scrape"] = {"status": "error", "error": str(e)}
        log_ingestion("RAPAStealthEngine", "carrier_scrape", "error", 0,
                      {"trigger_type": trigger_type, "error": str(e)}, db_path)

    # Stage 2 — OTA scrape
    try:
        ota_dumps = scrape_ota_basket(engine=engine, limit=6, throttle=True)
        result["stages"]["ota_scrape"] = {"status": "ok", "dumps": len(ota_dumps)}
        log_ingestion("OTAScraper", "ota_scrape", "success", len(ota_dumps),
                      {"trigger_type": trigger_type}, db_path)
    except Exception as e:
        logger.error("[CYCLE] OTA scrape failed: %s", e)
        result["stages"]["ota_scrape"] = {"status": "error", "error": str(e)}
        log_ingestion("OTAScraper", "ota_scrape", "error", 0,
                      {"trigger_type": trigger_type, "error": str(e)}, db_path)

    # Stage 3 — Parse dumps (only if GEMINI_API_KEY is set)
    if os.getenv("GEMINI_API_KEY"):
        try:
            from processor import run_pipeline
            run_pipeline(dumps_dir=dumps_dir, db_path=db_path)
            result["stages"]["parse_dumps"] = {"status": "ok"}
            log_ingestion("GeminiProcessor", "parse_dumps", "success", 0,
                          {"trigger_type": trigger_type}, db_path)
        except Exception as e:
            logger.error("[CYCLE] parse-dumps failed: %s", e)
            result["stages"]["parse_dumps"] = {"status": "error", "error": str(e)}
            log_ingestion("GeminiProcessor", "parse_dumps", "error", 0,
                          {"trigger_type": trigger_type, "error": str(e)}, db_path)
    else:
        logger.warning("[CYCLE] GEMINI_API_KEY not set — skipping parse-dumps stage.")
        result["stages"]["parse_dumps"] = {"status": "skipped", "reason": "GEMINI_API_KEY not set"}

    result["completed_at"] = datetime.now().isoformat()
    logger.info("[CYCLE] Full cycle complete: %s", result["stages"])
    return result


def get_scheduler_status(db_path: str = DB_PATH) -> dict:
    """Read last-run and next-run state from scheduler_runs table."""
    _ensure_scheduler_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM scheduler_runs ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"status": "not_started", "last_run_at": None, "next_run_at": None}


def start_scheduler(cron_expr: str = DEFAULT_CRON, db_path: str = DB_PATH) -> None:
    """
    Launch APScheduler BackgroundScheduler and block until Ctrl+C.
    This is a functional prototype scheduler — not production-hardened.

    Parameters
    ----------
    cron_expr : str
        5-field cron expression. Default: '30 21 * * *' (03:00 IST = 21:30 UTC).
    """
    if not HAS_APSCHEDULER:
        logger.error(
            "APScheduler is not installed. Run: pip install apscheduler\n"
            "Then re-run: python run.py schedule-start"
        )
        sys.exit(1)

    _ensure_scheduler_table(db_path)

    scheduler = BackgroundScheduler(timezone="UTC")

    def _scheduled_job():
        now = datetime.now().isoformat()
        # Compute approximate next run (next day same time)
        next_run = (datetime.now() + timedelta(days=1)).isoformat()
        _update_scheduler_state("running", now, next_run, None, db_path)
        try:
            result = run_full_cycle(trigger_type="scheduled", db_path=db_path)
            _update_scheduler_state("idle", now, next_run, str(result.get("stages")), db_path)
        except Exception as e:
            logger.error("[SCHEDULER] Job failed: %s", e)
            _update_scheduler_state("error", now, next_run, str(e), db_path)

    parts = cron_expr.strip().split()
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1],
        day=parts[2], month=parts[3], day_of_week=parts[4]
    )
    scheduler.add_job(_scheduled_job, trigger=trigger, id="rapa_daily_extraction")
    scheduler.start()

    # Compute first next_run approximation
    next_job = scheduler.get_job("rapa_daily_extraction")
    next_run_str = next_job.next_run_time.isoformat() if next_job and next_job.next_run_time else "unknown"
    _update_scheduler_state("idle", None, next_run_str, None, db_path)

    logger.info("[SCHEDULER] RAPA daily extraction scheduler started.")
    logger.info("[SCHEDULER] Cron: %s | Next run: %s", cron_expr, next_run_str)
    logger.info("[SCHEDULER] Press Ctrl+C to stop.")

    try:
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        _update_scheduler_state("stopped", None, None, None, db_path)
        logger.info("[SCHEDULER] Scheduler stopped gracefully.")


if __name__ == "__main__":
    start_scheduler()
