"""Retry wrapper for SQLite writes under concurrent access."""
import time
import sqlite3


def with_retry(fn, retries=4, base_delay=0.15):
    """
    Runs fn() and retries on 'database is locked' errors with backoff.
    fn should be a no-arg callable (use a lambda or closure).
    """
    for attempt in range(retries):
        try:
            return fn()
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < retries - 1:
                time.sleep(base_delay * (2 ** attempt))  # 0.15, 0.3, 0.6, 1.2s
                continue
            raise