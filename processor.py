# =============================================================================
# processor.py
# =============================================================================
# Purpose : End-to-end flight-quote ingestion pipeline.
#
# Pipeline stages:
#   1. DISCOVER  – scan ./raw_dumps/ for .html / .json / .txt files
#   2. EXTRACT   – call Gemini (structured outputs) with auto-retry (exponential backoff)
#   3. VALIDATE  – mathematical fare check + Z-score outlier detection
#   4. PERSIST   – insert clean records into SQLite
#
# Pre-requisites:
#   pip install google-genai pandas pydantic scipy
#   python db_setup.py            (creates the database schema)
#   set GEMINI_API_KEY=<your_key> (Windows) / export ... (Linux/macOS)
#
# Usage:
#   python processor.py
#   python processor.py --dumps ./my_other_dumps --db ./custom.db
# =============================================================================

from __future__ import annotations

import argparse
import logging
import os
import glob
import random
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
from scipy import stats
from google import genai
from google.genai import types

# Internal modules
from schema import FlightQuoteList
from db_setup import init_db, DB_NAME

# Load environment variables from a local .env file (if present).
# This lets developers store GEMINI_API_KEY in .env instead of the shell.
# The .env file is listed in .gitignore and must NEVER be committed to Git.
from dotenv import load_dotenv
load_dotenv()  # searches for .env in the current directory and parents

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_ID = "gemini-3.6-flash"

# Fare fields that must sum to total_fare
FARE_COMPONENTS = ["base_fare", "taxes", "user_development_fee", "convenience_charge"]

# Floating-point tolerance for math validation (0.01 = 1 paise tolerance)
MATH_TOLERANCE = 0.01

# Z-score threshold for price outlier flagging
ZSCORE_THRESHOLD = 3.0

# ---------------------------------------------------------------------------
# Retry / back-off configuration
# ---------------------------------------------------------------------------
# Maximum number of attempts per file before giving up
MAX_RETRIES = 4
# Initial wait in seconds before the first retry
RETRY_BASE_DELAY = 5.0
# Each retry multiplies the delay by this factor  (2 = exponential doubling)
RETRY_BACKOFF_FACTOR = 2.0
# Random jitter added to each delay (prevents thundering-herd on parallel runs)
RETRY_JITTER = 1.0
# Seconds to wait between processing each file (prevents burst 429s)
INTER_FILE_DELAY = 5.0
# Max chars to send to Gemini per file (large dumps burn through quota fast)
MAX_CONTENT_CHARS = 100_000

# File extensions to ingest from raw_dumps
SUPPORTED_EXTENSIONS = ("*.html", "*.htm", "*.json", "*.txt", "*.xml")


# =============================================================================
# STAGE 1 — DISCOVER
# =============================================================================

def discover_files(dumps_dir: str) -> list[str]:
    """
    Recursively collect all supported files under `dumps_dir`.

    Parameters
    ----------
    dumps_dir : str
        Path to the directory containing raw dump files.

    Returns
    -------
    list[str]
        Sorted list of absolute file paths.
    """
    if not os.path.isdir(dumps_dir):
        log.warning("Raw dumps directory not found: %s — creating it.", dumps_dir)
        os.makedirs(dumps_dir, exist_ok=True)

    paths: list[str] = []
    for pattern in SUPPORTED_EXTENSIONS:
        paths.extend(glob.glob(os.path.join(dumps_dir, "**", pattern), recursive=True))

    paths = sorted(set(paths))   # de-duplicate, ensure stable order
    log.info("Discovered %d file(s) in %s", len(paths), dumps_dir)
    return paths


# =============================================================================
# STAGE 2 — EXTRACT (Gemini Structured Output)
# =============================================================================

def build_system_prompt() -> str:
    """
    Returns the system instruction that tells Gemini exactly what to extract
    and how to handle ambiguous or missing fields.
    """
    return (
        "You are an expert data-extraction agent specialised in aviation pricing.\n"
        "You will receive raw HTML, JSON, or plain-text content scraped from a flight "
        "booking website.\n\n"
        "Your task:\n"
        "  • Identify every distinct flight quote present in the content.\n"
        "  • For EACH quote, extract the fields defined in the JSON schema exactly.\n"
        "  • Amounts must be numeric (float). Strip currency symbols (₹, INR, Rs).\n"
        "  • If a fare component (taxes, UDF, convenience) is not shown separately, "
        "    set it to 0.0 — do NOT guess.\n"
        "  • For departure_timestamp, prefer ISO-8601 (YYYY-MM-DDTHH:MM:SS). "
        "    If only a date is present, append 'T00:00:00'.\n"
        "  • For seat_status, use 'available' unless the page explicitly shows "
        "    'sold out', 'fully booked', or 'cancelled' — then use 'sold-out' or "
        "    'cancelled' respectively.\n"
        "  • Return an empty quotes list if NO flight data is found.\n"
        "  • Do NOT invent data. If a field is truly absent, use an empty string "
        "    for text fields or 0.0 for numeric fields.\n"
    )


def extract_quotes_from_file(
    client: genai.Client,
    file_path: str,
) -> list[dict]:
    """
    Send one raw dump file to Gemini and return extracted quotes as dicts.

    Parameters
    ----------
    client : genai.Client
        Authenticated Gemini API client.
    file_path : str
        Absolute path to the raw dump file.

    Returns
    -------
    list[dict]
        List of quote dicts (Pydantic model_dump output), or [] on failure.
    """
    log.info("Extracting → %s", Path(file_path).name)

    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.error("Cannot read file %s: %s", file_path, exc)
        return []

    if not content.strip():
        log.warning("File is empty, skipping: %s", file_path)
        return []

    # Gemini has a context window limit; warn if file is very large
    if len(content) > MAX_CONTENT_CHARS:
        log.warning(
            "File %s is very large (%d chars). Truncating to %d chars to stay within token quota.",
            Path(file_path).name,
            len(content),
            MAX_CONTENT_CHARS,
        )
        content = content[:MAX_CONTENT_CHARS]

    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info(
                "  Attempt %d/%d — calling %s ...",
                attempt, MAX_RETRIES, MODEL_ID,
            )

            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text="Extract all flight quotes from the content below:"),
                            types.Part(text=content),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    # System instruction (extraction persona)
                    system_instruction=build_system_prompt(),
                    # Enforce structured JSON output matching our Pydantic schema
                    response_mime_type="application/json",
                    response_schema=FlightQuoteList,
                    # temperature=0 → deterministic, no hallucination creativity
                    temperature=0.0,
                ),
            )

            if not response.parsed:
                log.warning(
                    "Gemini returned no parsed output for %s (attempt %d)",
                    Path(file_path).name, attempt,
                )
                return []

            result: FlightQuoteList = response.parsed
            quotes = [q.model_dump() for q in result.quotes]

            # Stamp every quote with its origin file for the audit column
            for q in quotes:
                q["source_file"] = Path(file_path).name

            log.info("  ✓ Extracted %d quote(s) on attempt %d", len(quotes), attempt)
            return quotes

        except Exception as exc:
            last_exc = exc

            if attempt == MAX_RETRIES:
                log.error(
                    "All %d attempts failed for %s. Last error: %s",
                    MAX_RETRIES, Path(file_path).name, exc,
                )
                break

            # Check if the API told us exactly how long to wait (429 retryDelay)
            api_wait: float | None = None
            exc_str = str(exc)
            if "retryDelay" in exc_str or "429" in exc_str:
                import re as _re
                m = _re.search(r"retryDelay.*?(\d+)s", exc_str)
                if m:
                    api_wait = float(m.group(1)) + 2.0   # add 2s buffer
                    log.warning(
                        "Rate-limited (429). API requests we wait %ds. Sleeping %.0fs ...",
                        int(m.group(1)), api_wait,
                    )

            if api_wait is None:
                # Exponential backoff: delay = base * (factor ^ (attempt-1)) + jitter
                api_wait = (
                    RETRY_BASE_DELAY
                    * (RETRY_BACKOFF_FACTOR ** (attempt - 1))
                    + random.uniform(0, RETRY_JITTER)
                )
                log.warning(
                    "Attempt %d/%d failed for %s: %s — retrying in %.1fs ...",
                    attempt, MAX_RETRIES, Path(file_path).name, exc, api_wait,
                )

            time.sleep(api_wait)

    return []  # all retries exhausted


# =============================================================================
# STAGE 3 — VALIDATE
# =============================================================================

def math_validation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add `is_math_valid` column.

    Rule: total_fare ≈ base_fare + taxes + user_development_fee + convenience_charge
    Tolerance: ±0.01 (one paise) to handle floating-point rounding.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame of extracted quotes.

    Returns
    -------
    pd.DataFrame
        Same DataFrame with `is_math_valid` (bool) column appended.
    """
    calculated = df[FARE_COMPONENTS].sum(axis=1)
    df["is_math_valid"] = (df["total_fare"] - calculated).abs() < MATH_TOLERANCE

    invalid_count = (~df["is_math_valid"]).sum()
    if invalid_count > 0:
        log.warning(
            "Math validation failed for %d record(s). "
            "total_fare does not equal sum of components (within ±%.2f).",
            invalid_count,
            MATH_TOLERANCE,
        )
        # Log the offending rows for debugging
        bad = df[~df["is_math_valid"]][["flight_number", "total_fare"] + FARE_COMPONENTS]
        log.debug("Invalid records:\n%s", bad.to_string())
    else:
        log.info("Math validation passed for all %d record(s).", len(df))

    return df


def zscore_outlier_detection(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add `is_price_outlier` column using Z-scores on `total_fare`.

    A record is flagged as an outlier when |z-score| > ZSCORE_THRESHOLD (3).
    Requires at least 2 records; otherwise all rows are marked non-outlier.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame (must already contain `total_fare` column).

    Returns
    -------
    pd.DataFrame
        Same DataFrame with `is_price_outlier` (bool) column appended.
    """
    if len(df) < 2:
        log.warning(
            "Only %d record(s) — Z-score outlier detection requires ≥2. "
            "Marking all as non-outlier.",
            len(df),
        )
        df["is_price_outlier"] = False
        return df

    z_scores = stats.zscore(df["total_fare"], ddof=1)   # sample std dev
    df["is_price_outlier"] = z_scores.abs() > ZSCORE_THRESHOLD

    outlier_count = df["is_price_outlier"].sum()
    if outlier_count > 0:
        log.warning(
            "%d price outlier(s) detected (|z| > %.1f):",
            outlier_count,
            ZSCORE_THRESHOLD,
        )
        for _, row in df[df["is_price_outlier"]].iterrows():
            log.warning(
                "  Flight %s | total_fare=%.2f | z=%.2f",
                row["flight_number"],
                row["total_fare"],
                z_scores[row.name],
            )
    else:
        log.info("No price outliers detected.")

    return df


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Run all validation stages and return the enriched DataFrame."""
    log.info("--- Running Validation ---")
    df = math_validation(df)
    df = zscore_outlier_detection(df)
    return df


# =============================================================================
# STAGE 4 — PERSIST (SQLite)
# =============================================================================

# Columns that exist in the DB table (keeps to_sql from inserting unknowns)
DB_COLUMNS = [
    "flight_number", "airline", "origin_sector", "destination_sector",
    "departure_timestamp", "base_fare", "taxes", "user_development_fee",
    "convenience_charge", "total_fare", "seat_status",
    "is_math_valid", "is_price_outlier", "source_file",
]


def insert_to_db(df: pd.DataFrame, db_path: str) -> None:
    """
    Insert all validated records into the `flight_quotes` SQLite table.

    We use `if_exists='append'` so we never drop existing data.
    The `id` and `ingestion_timestamp` columns are handled automatically
    by SQLite defaults.

    Parameters
    ----------
    df : pd.DataFrame
        Validated DataFrame containing the columns listed in DB_COLUMNS.
    db_path : str
        Absolute path to the SQLite database file.
    """
    # Keep only columns that exist in the schema to avoid to_sql errors
    available_cols = [c for c in DB_COLUMNS if c in df.columns]
    df_to_insert = df[available_cols].copy()

    # SQLite stores booleans as integers; convert
    for bool_col in ["is_math_valid", "is_price_outlier"]:
        if bool_col in df_to_insert.columns:
            df_to_insert[bool_col] = df_to_insert[bool_col].astype(int)

    try:
        conn = sqlite3.connect(db_path)
        df_to_insert.to_sql("flight_quotes", conn, if_exists="append", index=False)
        conn.close()
        log.info("Inserted %d record(s) into %s → flight_quotes", len(df_to_insert), db_path)
    except Exception as exc:
        log.error("Failed to insert into SQLite: %s", exc)
        raise


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_pipeline(dumps_dir: str, db_path: str) -> None:
    """
    Orchestrates the four pipeline stages.

    Parameters
    ----------
    dumps_dir : str
        Directory containing raw HTML/JSON dump files.
    db_path : str
        Path to the target SQLite database.
    """
    # Ensure DB schema exists before anything else
    init_db(db_path)

    # Stage 1 — Discover
    files = discover_files(dumps_dir)
    if not files:
        log.error(
            "No supported files found in %s. "
            "Add .html / .json / .txt files and re-run.",
            dumps_dir,
        )
        sys.exit(1)

    # Stage 2 — Extract via Gemini
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error(
            "GEMINI_API_KEY environment variable is not set. "
            "Set it with:\n"
            "  Windows PowerShell : $env:GEMINI_API_KEY = 'your_key_here'\n"
            "  Linux / macOS      : export GEMINI_API_KEY='your_key_here'"
        )
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    all_quotes: list[dict] = []
    for i, file_path in enumerate(files):
        quotes = extract_quotes_from_file(client, file_path)
        all_quotes.extend(quotes)
        # Polite inter-file delay to avoid rate-limit cascades on large batches
        if i < len(files) - 1:
            log.info("Waiting %.0fs before next file ...", INTER_FILE_DELAY)
            time.sleep(INTER_FILE_DELAY)

    if not all_quotes:
        log.error("No quotes could be extracted from any file. Exiting.")
        sys.exit(1)

    # Stage 3 — Build DataFrame and validate
    df = pd.DataFrame(all_quotes)
    log.info("Total quotes extracted across all files: %d", len(df))

    df = validate(df)

    # Summary report
    log.info("--- Validation Summary ---")
    log.info("  Total records        : %d", len(df))
    log.info("  Math valid           : %d", df["is_math_valid"].sum())
    log.info("  Math INVALID         : %d", (~df["is_math_valid"]).sum())
    log.info("  Price outliers       : %d", df["is_price_outlier"].sum())

    # Stage 4 — Persist
    insert_to_db(df, db_path)

    log.info("Pipeline complete. Database: %s", db_path)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse optional CLI overrides for dumps directory and database path."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description="Flight Quote Ingestion Pipeline — powered by Gemini Structured Outputs"
    )
    parser.add_argument(
        "--dumps",
        default=os.path.join(script_dir, "raw_dumps"),
        help="Path to directory containing raw HTML/JSON dumps (default: ./raw_dumps/)",
    )
    parser.add_argument(
        "--db",
        default=os.path.join(script_dir, DB_NAME),
        help=f"Path to SQLite database file (default: ./{DB_NAME})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(dumps_dir=args.dumps, db_path=args.db)
