"""
Background Automated Ingestion Scheduler for RAPA.
Provides:
1. Periodic recurring collection of live flight quotes via Ignav REST API.
2. Automatic re-calculation of high-frequency Jevons index and MoSPI validation.
3. State tracking (last_run, next_run, status, total_cycles) in SQLite / JSON metadata.
"""

import time
import threading
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fares.collector import collect_route_fares
from data.db import log_ingestion, DB_PATH

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "scheduler_state.json")


def get_scheduler_state() -> Dict[str, Any]:
    """Reads current background scheduler state."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "status": "STOPPED",
        "last_run": None,
        "next_run": None,
        "interval_seconds": 300,
        "total_cycles_completed": 0,
        "last_quotes_collected": 0,
        "last_error": None
    }


def save_scheduler_state(state: Dict[str, Any]) -> None:
    """Persists scheduler state to JSON file."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


class BackgroundSchedulerDaemon:
    """Threaded daemon for automated recurring fare collection."""

    def __init__(self, interval_seconds: int = 300, db_path: str = DB_PATH):
        self.interval_seconds = interval_seconds
        self.db_path = db_path
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        state = get_scheduler_state()
        state["status"] = "STOPPED"
        save_scheduler_state(state)

    def trigger_once(self) -> Dict[str, Any]:
        """Runs a single live ingestion and index calculation cycle immediately."""
        start_ts = datetime.now()
        try:
            res = collect_route_fares(db_path=self.db_path)
            q_count = res.get("total_quotes_collected", 0)
            state = get_scheduler_state()
            state["last_run"] = start_ts.isoformat()
            state["last_quotes_collected"] = q_count
            state["total_cycles_completed"] = state.get("total_cycles_completed", 0) + 1
            state["last_error"] = None
            save_scheduler_state(state)
            return {
                "status": "SUCCESS",
                "quotes_collected": q_count,
                "timestamp": start_ts.isoformat(),
                "details": res
            }
        except Exception as e:
            state = get_scheduler_state()
            state["last_error"] = str(e)
            save_scheduler_state(state)
            raise

    def _run_loop(self):
        state = get_scheduler_state()
        state["status"] = "RUNNING"
        state["interval_seconds"] = self.interval_seconds
        save_scheduler_state(state)

        while self._running:
            now = datetime.now()
            next_run = now + timedelta(seconds=self.interval_seconds)

            state = get_scheduler_state()
            state["status"] = "RUNNING"
            state["next_run"] = next_run.isoformat()
            save_scheduler_state(state)

            try:
                self.trigger_once()
            except Exception as e:
                pass

            # Sleep in 1-second chunks to allow responsive shutdown
            for _ in range(self.interval_seconds):
                if not self._running:
                    break
                time.sleep(1)


# Global singleton daemon instance
scheduler_daemon = BackgroundSchedulerDaemon()
