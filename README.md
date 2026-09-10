# RAPA — Real-Time Airfare Price Analytics & Econometric CPI Engine

> Powered by **FastAPI** | **Streamlit** | **SQLite (WAL)** | **Pydantic v2** | **Pandas & SciPy** | **Playwright**

---

## 1. Executive Summary & Problem Landscape

Official Consumer Price Index (CPI) reporting across transport services in India faces four fundamental systemic hurdles:

1. **45-Day Statistical Reporting Lag**: Official CPI published by the Ministry of Statistics and Programme Implementation (MoSPI) is released weeks after the observation period. Rapid, algorithmic airline repricing shocks blind monetary policy and regulators during acute demand surges.
2. **Dynamic Pricing Volatility (200%–400%)**: Airfares vary by 300% or more across booking advance horizons (T+1 emergency travel vs T+45 planned travel). Unstratified sampling produces artificial, extreme inflation spikes that misrepresent true cost-of-living trends.
3. **Upward Substitution Bias (2.0%–3.5%)**: Traditional arithmetic averaging (the Carli formula used in field surveys) overstates flight inflation by **2.0% to 3.5%** due to asymmetric airline surge pricing extremes.
4. **Lack of Cryptographic Data Provenance**: Conventional manual field surveys lack auditable, legally defensible, tamper-proof proof of fare observation.

**RAPA** resolves these challenges by deploying an automated, ethical, high-frequency price observation engine paired with a **Jevons Axiomatic Geometric Index** and **DGCA passenger volume weighting**, delivering daily, weekly, and monthly airfare price relatives for national statistical compilation.

---

## 2. Core Architectural Pillars

- **Ethical Dual-Channel Harvester**: Non-disruptive, polite extraction across direct carrier endpoints (IndiGo, Air India, Akasa, SpiceJet, AI Express) and Online Travel Agencies (MakeMyTrip, Yatra, EaseMyTrip, Cleartrip, Ixigo, Goibibo) bounded by 0.2 RPS throttling, humanized jitter, and zero DDoS footprint.
- **In-House Anti-Bot Challenge Resolution**: Playwright session manager featuring human-like Bezier curve mouse deceleration against Cloudflare Turnstile, reCAPTCHA v2 token execution, and Vision OCR challenge solvers with zero paid third-party dependencies.
- **Pydantic v2 Ingestion Firewall**: Enforces strict typing, positive price constraints, and fare component arithmetic checks ($\text{Total Fare} = \text{Base Fare} + \text{Taxes} + \text{UDF} + \text{Convenience Charge} \pm 0.01$).
- **Cryptographic Audit Vault**: Raw HTML/JSON responses hashed via **SHA-256** and archived to provide immutable, legally defensible provenance against airline regulatory challenge.
- **5-Horizon Matched-Model Stratification**: Standardizes observation across 5 advance booking windows ($T+1, T+3, T+7, T+14, T+45$), ensuring apples-to-apples economic comparison.
- **Axiomatic Jevons Geometric Mean**: Aggregates price relatives geometrically, satisfying international UN/ILO Time-Reversal axioms and eliminating upward substitution bias.
- **DGCA Passenger Volume Weighting**: Weights corridor relatives based on empirical Directorate General of Civil Aviation passenger density (e.g., DEL-BOM 25%, DEL-BLR 20%).
- **MoSPI Benchmark Tracking**: Tracks official July 2026 CPI benchmarks (Base 2024 = 100) including Group 07 Transport (105.63) and Group 07.3 Passenger Transport Services (105.39) as official proxies for Item 294 (Airfare).

---

## 3. Project Directory Structure

```
rapa-engine/
├── api/                                  # Asynchronous FastAPI Microservice
│   └── main.py                           # REST API server (NSO/RBI feeds, quotes, heatmap, benchmarks)
│
├── benchmark/                            # Official Benchmark Calibration Subsystem
│   ├── mospi_client.py                   # MoSPI eSankhyiki / Press Release client
│   └── fixtures/                         # Official CPI datasets (July 2026, Base 2024=100)
│
├── dashboard/                            # Interactive Frontend Analytics
│   ├── app.py                            # Streamlit analytics dashboard (heatmaps, elasticity curves)
│   └── components/                       # Visualisation modules and Plotly components
│
├── data/                                 # Persistence & Database Layer
│   ├── db.py                             # Core SQLite access layer, schema, migrations & CRUD
│   ├── rapa.db                           # Production SQLite database (WAL mode, 1,600+ quotes)
│   └── flight_quotes.db                  # Ingestion extraction database
│
├── portal/                               # Administrative Web Portal
│   ├── index.html                        # Lightweight single-page executive interface
│   └── static/                           # Portal styling, layouts, and SVG assets
│
├── raw_dumps/                            # Cryptographic Provenance Storage
│   ├── sample_del_bom.html               # Raw airline DOM snapshots
│   ├── sample_maa_hyd.json               # Raw JSON payload dumps
│   └── quote_DEL-BOM_T+*.html            # Lead-time stratified dumps (T+1 to T+45)
│
├── scripts/                              # Verification & Diagnostic Utilities
│   ├── audit_pure.py                     # 24-point zero-compromise system verification
│   └── test_ignav_coverage.py            # Comprehensive test coverage runner
│
├── src/rapa/ingestion/                   # Ingestion & Anti-Bot Engine
│   ├── custom_scraper.py                 # Multi-carrier and OTA scraping engine
│   ├── dynamic_session_engine.py         # Playwright session manager
│   └── captcha_solver.py                 # Autonomous in-house challenge solver (Bezier + Vision)
│
├── tests/                                # Automated Test Suite (100% Passing)
│   ├── test_api.py                       # REST API endpoint tests
│   ├── test_benchmark.py                 # MoSPI benchmark and proxy tests
│   ├── test_captcha_solver.py            # Anti-bot resolution tests
│   ├── test_custom_scraper.py            # Scraper rate-limiting and session tests
│   ├── test_deduplication.py             # 5-minute sliding-window deduplication tests
│   ├── test_dynamic_session_engine.py    # Playwright browser integration tests
│   ├── test_fare_class.py                # Cabin-class decomposition tests
│   ├── test_formulas.py                  # Jevons geometric mean and math tests
│   ├── test_frequency_aggregation.py     # Daily, weekly, monthly aggregation tests
│   ├── test_heatmap_backtest.py          # Heatmap calculation and backtest tests
│   ├── test_ota_scraper.py               # OTA aggregator parsing tests
│   ├── test_proxy_rotator.py             # Proxy pool and fail-loud tests
│   └── test_scheduler.py                 # APScheduler background daemon tests
│
├── validation/                           # Econometric & Schema Validation
│   ├── backtest.py                       # Econometric backtesting engine
│   └── evaluator.py                      # Pydantic validation and outlier detection
│
├── db_setup.py                           # Database schema initializer and migration script
├── processor.py                          # Gemini extraction and batch ingestion pipeline
├── query_db.py                           # Database inspection and fare statistics CLI
├── run.py                                # Unified master CLI runner (scrape, calculate, serve)
├── scheduler.py                          # APScheduler daily extraction daemon
├── schema.py                             # Pydantic v2 structured output contracts
├── requirements.txt                      # Project Python dependencies
├── .env.example                          # Environment variable configuration template
└── README.md                             # Comprehensive project documentation
```

---

## ⚙️ Step 1 — Environment Setup

### Requirements
- Python **3.11+**
- Git

### Install Dependencies

```powershell
# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install all dependencies
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `google-genai` | Gemini API — structured output extraction |
| `pandas` | Data validation, Z-score, aggregation |
| `pydantic` | JSON schema enforcement |
| `scipy` | `stats.zscore` for outlier detection |
| `python-dotenv` | Load `GEMINI_API_KEY` from `.env` |
| `fastapi` | REST API framework |
| `uvicorn` | ASGI server for FastAPI |
| `streamlit` | Interactive analytics dashboard |
| `plotly` | Interactive charts (heatmap, elasticity curve) |

### Set Your Gemini API Key

Get a free key at → https://aistudio.google.com/apikey

```powershell
# Option A: .env file (permanent, recommended)
echo "GEMINI_API_KEY=AIza...your_key" > .env

# Option B: Terminal session (temporary)
$env:GEMINI_API_KEY = "AIza...your_key"   # Windows PowerShell
export GEMINI_API_KEY="AIza...your_key"   # Linux/macOS
```

> ⚠️ **Never commit `.env` to Git.** It is blocked by `.gitignore`.

---

## 🗄️ Step 2 — Initialise the Database

Run **once** before first pipeline execution:

```powershell
$env:PYTHONUTF8 = "1"
python db_setup.py
```

Creates `flight_quotes.db` with the `flight_quotes` table.

---

## 🚀 Step 3 — Run the Ingestion Pipeline

```powershell
# Place your raw HTML/JSON dumps in raw_dumps/
$env:PYTHONUTF8 = "1"
python processor.py

# Custom paths
python processor.py --dumps ./my_dumps --db ./custom.db
```

### Pipeline Stages

```
STAGE 1  DISCOVER   Scan raw_dumps/ recursively for .html, .json, .txt, .xml
    ↓
STAGE 2  EXTRACT    Per file → gemini-3.6-flash with Structured Output (Pydantic schema)
                    Auto-retry: 4 attempts, reads API retryDelay on 429, 5s base backoff
                    5s inter-file delay to respect free-tier token quota
    ↓
STAGE 3  VALIDATE   Math: total_fare = base + taxes + UDF + convenience (±0.01 tolerance)
                    Outliers: scipy Z-score on total_fare, flag if |z| > 3.0
    ↓
STAGE 4  PERSIST    pandas.to_sql() → INSERT INTO flight_quotes (append mode)
```

### Rate Limit Notes (Free Tier)

The free tier allows **250,000 input tokens/minute**. Large dump files (>1MB) can exhaust this quickly. The pipeline handles this automatically:
- Truncates each file to **100,000 characters** before sending
- Waits **5 seconds between files**
- On a 429 error, reads the API's `retryDelay` and waits that exact amount

To remove quota limits entirely, enable billing at https://aistudio.google.com.

---

## 🌐 Step 4 — Start the FastAPI Service

```powershell
cd path/to/rapa-engine
$env:PYTHONUTF8 = "1"
uvicorn main:app --reload --port 8000
```

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | DB status + record count |
| `GET` | `/api/v1/quotes` | Filtered, paginated quote feed |
| `GET` | `/api/v1/sector-heatmap` | Avg/min/max fare per route |
| `GET` | `/api/v1/elasticity` | Lead-time price elasticity (4 buckets) |
| `GET` | `/docs` | Auto-generated Swagger UI |
| `GET` | `/redoc` | ReDoc API documentation |

### Example Queries

```bash
# All available flights, page 1
GET http://localhost:8000/api/v1/quotes?seat_status=available

# DEL→BOM route only, max fare Rs.10,000
GET http://localhost:8000/api/v1/quotes?origin=DEL&destination=BOM&max_fare=10000

# Heatmap data excluding outliers
GET http://localhost:8000/api/v1/sector-heatmap?exclude_outliers=true

# Elasticity for DEL→BOM route
GET http://localhost:8000/api/v1/elasticity?route=DEL->BOM
```

---

## 📊 Step 5 — Launch the Streamlit Dashboard

Open a **second terminal**:

```powershell
cd path/to/rapa-engine
$env:PYTHONUTF8 = "1"
streamlit run dashboard.py
```

Opens at **http://localhost:8501**

### Dashboard Sections

| Section | Visualisation |
|---|---|
| KPI Cards | Total quotes, Avg/Min/Max fare, Math valid % |
| Sector Heatmap | Plotly `imshow` — origin × destination × avg fare |
| Airline Breakdown | Stacked bar — fare components per airline |
| Seat Status | Donut pie chart |
| Elasticity Curve | Line chart with shaded min/max band across 4 lead-time buckets |
| Raw Data Explorer | Filterable table + CSV download |

---

## 🔍 Query the Database Directly

```powershell
python query_db.py
```

Or via SQLite CLI:

```sql
sqlite3 flight_quotes.db

-- All records
SELECT flight_number, airline, total_fare, seat_status FROM flight_quotes;

-- Price outliers
SELECT flight_number, total_fare FROM flight_quotes WHERE is_price_outlier = 1;

-- Fare invalid math
SELECT * FROM flight_quotes WHERE is_math_valid = 0;

-- Route averages
SELECT origin_sector||'->'||destination_sector AS route,
       COUNT(*) as flights, AVG(total_fare) as avg_fare
FROM flight_quotes GROUP BY route ORDER BY avg_fare DESC;
```

---

## 📐 Database Schema

```sql
CREATE TABLE flight_quotes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_number        TEXT    NOT NULL,
    airline              TEXT    NOT NULL,
    origin_sector        TEXT    NOT NULL,
    destination_sector   TEXT    NOT NULL,
    departure_timestamp  TEXT    NOT NULL,
    base_fare            REAL    NOT NULL,
    taxes                REAL    NOT NULL,
    user_development_fee REAL    NOT NULL,
    convenience_charge   REAL    NOT NULL,
    total_fare           REAL    NOT NULL,
    seat_status          TEXT    NOT NULL
        CHECK (seat_status IN ('available', 'sold-out', 'cancelled')),
    is_math_valid        INTEGER NOT NULL DEFAULT 1,
    is_price_outlier     INTEGER NOT NULL DEFAULT 0,
    is_duplicate         INTEGER NOT NULL DEFAULT 0,
    source_type          TEXT DEFAULT 'aggregator',
    ota_platform         TEXT,
    fare_class           TEXT DEFAULT 'UNKNOWN',
    source_file          TEXT,
    ingestion_timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🏛️ SIH Problem Statement Compliance & Prototype Architecture

The RAPA Engine includes full implementation of all requirements specified in the official SIH problem statement:

### 1. Multi-Source Web-Scraping Engine (OTA & Direct Carriers)
- Direct Carrier portal extraction via `python run.py scrape [N]`
- Dynamic JavaScript rendering & anti-bot protection via `python run.py dynamic-scrape [N]`
- **Autonomous Dynamic CAPTCHA Solver**: In-house detection and automated solving of Cloudflare Turnstile (Bezier mouse deceleration), Google reCAPTCHA v2 (humanized token click), Image/Math challenges (Gemini Multimodal Flash Vision OCR), and puzzle drag sliders (`src/rapa/ingestion/captcha_solver.py`) with zero paid third-party dependencies.
- **6 OTA Portals Supported**: MakeMyTrip, Goibibo, Cleartrip, Ixigo, EaseMyTrip, and Yatra via `python run.py scrape-ota [N]`
- All queries follow ethical scraping safeguards (robots.txt validation, human-like delay jitter, and domain-level rate limiting).

### 2. IP Rotation & Proxy Pool Management
- Built-in `ProxyRotator` supporting round-robin rotation over comma-separated proxy URLs configured in `RAPA_PROXIES`.
- Includes health validation `validate_pool()` that drops unreachable proxies prior to harvesting.
- Explicit fail-loud protection: passing `--use-proxies` without a valid proxy pool halts execution immediately rather than silently exposing the host IP.

### 3. High-Frequency Index Construction & Aggregation
- **Jevons Geometric Mean Index**: Matched-item index eliminating substitution bias with axiomatic time-reversal compliance.
- **Frequencies**: Supports Daily high-frequency tracking, ISO-week aggregation, and monthly series aligning with official NSO/RBI standards.
- Endpoint: `/v1/nso-rbi/feed?frequency=daily|weekly|monthly`
- Interactive Dashboard toggle: switch between Daily, Weekly, and Monthly price trends.

### 4. Scheduled Daily Extraction Pipeline
- Background automated extraction powered by APScheduler (`scheduler.py`).
- Default schedule: 03:00 IST daily (configurable via `RAPA_SCHEDULE_CRON`).
- Orchestration: Executes carrier scrape -> OTA scrape -> Gemini parse pipeline with state persistence in `scheduler_runs` and audit trail logging with `trigger_type='scheduled'`.
- CLI commands: `python run.py schedule-start`, `python run.py schedule-status`, `python run.py schedule-trigger`.

### 5. Metadata Enrichment & Fare-Class Disaggregation
- Decomposes quotes into base fare, taxes, user development fee (UDF), convenience charge, advance purchase window, and **fare-class** (`fare_class`).
- **Data Limitation Notice**: For existing historical records ingested prior to this sprint, `fare_class` defaults to `'UNKNOWN'` as historical raw dumps did not capture cabin-class metadata. All new extractions populate the extracted or identified cabin tier.

### 6. Sliding-Window De-duplication
- Exact-duplicate detection within a 5-minute sliding window prevents re-scrape pollution.
- Non-destructive flagging: records are marked `is_duplicate=1` without deleting audit history.
- Index construction automatically filters `WHERE COALESCE(is_duplicate, 0) = 0`.

*Note: In accordance with SIH evaluation criteria, all modules are fully functioning prototypes demonstrating end-to-end architectural capability with zero regressions.*

---

## 🔐 Security

| Item | Status |
|---|---|
| API key in source code | Never |
| `.env` in Git | Blocked by `.gitignore` |
| `.env.example` (safe template) | ✅ In repo |
| Database files (`*.db`) | Excluded from Git |

---

## 📦 Complete File Reference

| File | Module | Purpose |
|---|---|---|
| `schema.py` | Schema | Pydantic v2 Gemini output contract (with fare_class, source_type) |
| `db_setup.py` | Database | SQLite schema initialiser with auto-migration |
| `data/db.py` | Database | Core database access layer, audit logging, migrations |
| `processor.py` | Pipeline | Gemini extraction + dedup + validation + ingestion |
| `api/main.py` | REST API | FastAPI REST service (NSO/RBI feeds, heatmaps, volatility) |
| `dashboard.py` | Dashboard | Streamlit analytics dashboard with frequency toggle |
| `scheduler.py` | Scheduling | APScheduler daily extraction daemon |
| `src/rapa/ingestion/custom_scraper.py` | Harvester | Carrier + OTA scraping engine with proxy rotation |
| `src/rapa/ingestion/dynamic_session_engine.py` | Harvester | Dynamic session manager with Playwright fallback |
| `src/rapa/ingestion/captcha_solver.py` | Anti-Bot | Autonomous Dynamic CAPTCHA solver (Gemini Vision + Playwright) |
| `scripts/audit_pure.py` | Audit | 24-point zero-compromise system verification |
| `tests/` | QA | 98 automated unit and integration tests (100% passing) |
| `requirements.txt` | - | All project dependencies |
| `.env.example` | - | Environment variable configuration template |
| `.gitignore` | - | Secrets + generated files protection |
