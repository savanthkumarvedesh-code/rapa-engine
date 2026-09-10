# RAPA Engine

**Real-Time Airfare Price Augmentation — High-Frequency CPI Augmentation System**

Smart India Hackathon (SIH) — Ministry of Statistics and Programme Implementation (MoSPI)

---

## Overview

RAPA Engine is a high-frequency airfare intelligence platform that collects, indexes, and analyzes real-time domestic flight pricing across India's six major trunk aviation corridors. The system augments the official MoSPI Consumer Price Index (CPI) Item 294 (Airfare, Base 2024=100) with live market-rate fare microdata, enabling more accurate and timely cost-of-living measurement in the transportation sub-component.

The platform runs a multi-phase data pipeline:

1. **Static Stealth Harvester** — Scrapes raw fare HTML from carrier endpoints across 6 routes x 5 booking horizons
2. **Dynamic Session Engine** — Playwright-based DOM capture for JavaScript-rendered fare pages
3. **Gemini Flash Parsing Pipeline** — AI-powered extraction of structured fare records from raw HTML dumps
4. **Index Computation** — Matched-item Jevons geometric index calculated against a December 2025 baseline
5. **MoSPI Calibration** — Statistical divergence analysis against official CPI Item 294 benchmark values
6. **FastAPI Portal** — REST API and web dashboard serving all computed metrics

---

## Key Features

| Feature | Description |
|---|---|
| National Airfare Index | Composite Jevons geometric price index across all 6 corridors (Base: Dec 2025 = 100.0) |
| MoSPI CPI Benchmark Integration | Live ingestion from eSankhyiki official API — Item 294 Airfare (Base 2024=100) |
| Trunk Corridor Monitoring | Real-time fare tracking across 6 major domestic routes with DGCA basket weights |
| Lead-Time Yield Curves | Fare-vs-advance-booking curves across 5 horizon windows (T+1, T+7, T+15, T+30, T+45) |
| Sector Heatmap Matrix | 2D pricing density map across corridors and booking horizons with elasticity gradients |
| Live Flight Microdata Stream | Quote-level data feed from the stealth harvesting engine |
| Route Network Map | Geographic airport node map with coordinates, distances, and pricing overlays |
| DGCA Route Weight Adjuster | Applies official DGCA passenger traffic weights to normalize the composite index |
| Statistical Governance | Outlier detection using Tukey IQR fences and Z-score (|Z| > 2.5) |
| Multi-Formula Index Lab | Custom index computation — Jevons, Carli, Dutot, Laspeyres, Tornqvist |
| NSO / RBI Feed | SDMX-aligned machine-readable daily/weekly/monthly index feed |
| Automated Scheduler Daemon | Background ingestion scheduler with configurable intervals |
| Multi-Format Export | CSV and JSON export for fare quotes, CPI records, index values, and audit logs |
| Live Telemetry Logs | Rotating file-based server logs with per-request latency tracking |

---

## Monitored Corridors

| Sector | Route | Distance | Annual Passengers | Basket Weight |
|--------|-------|----------|-------------------|---------------|
| DEL-BOM | Delhi to Mumbai | 1,148 km | 4,820,000 | 25.0% |
| DEL-BLR | Delhi to Bengaluru | 1,740 km | 4,120,000 | 22.0% |
| BOM-BLR | Mumbai to Bengaluru | 842 km | 3,280,000 | 18.0% |
| DEL-CCU | Delhi to Kolkata | 1,305 km | 2,610,000 | 15.0% |
| BLR-HYD | Bengaluru to Hyderabad | 502 km | 2,150,000 | 10.0% |
| MAA-DEL | Chennai to Delhi | 1,760 km | 1,950,000 | 10.0% |

**Booking Horizons**: T+1 (next-day surge) / T+7 (short-notice) / T+15 (mid-horizon) / T+30 (advance baseline) / T+45 (early leisure)

---

## Tech Stack

**Backend and API**
- Python 3.10+
- FastAPI 0.111+ — REST API and portal server
- Uvicorn — ASGI server
- Pydantic v2 — Request/response validation
- SQLite — Local data persistence (fare quotes, CPI benchmarks, index values, audit logs)
- APScheduler 3.10+ — Background ingestion daemon

**Data Collection**
- Scrapling + Playwright — Stealth DOM harvesting engine (Phase 1 static + Phase 2 dynamic)
- google-genai 1.0+ — Gemini Flash parsing pipeline for structured fare extraction from raw HTML
- python-dotenv — Environment configuration

**Data Processing and Analytics**
- Pandas 2.0+ — Fare microdata processing, index computation
- SciPy 1.11+ — Statistical analysis (Pearson r, RMSE, MAPE, IQR outlier detection)

**Dashboard and Visualization**
- Streamlit 1.35+ — Alternative Streamlit dashboard
- Plotly 5.22+ — Interactive charts
- HTML / CSS / JavaScript — Primary web portal (served via FastAPI at `/portal/index.html`)

**Official Data Sources**
- MoSPI eSankhyiki API — CPI Item 294 Airfare (Base 2024=100), Group 07.3 Transport Proxy (Base 2012=100)

---

## Project Structure

```
rapa-engine/
├── run.py                    # Unified CLI entry point (all commands)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .env                      # Local secrets (gitignored)
├── session_state.json        # Dynamic session engine state
│
├── api/
│   ├── main.py               # FastAPI app — all REST endpoints (v2.1.0)
│   └── stream_routes.py      # Server-Sent Events streaming routes
│
├── benchmark/
│   └── mospi_client.py       # MoSPI eSankhyiki CPI ingestion client
│
├── fares/
│   ├── collector.py          # Batch fare collection orchestrator
│   ├── scraper_client.py     # Stealth scraper fare collector (primary)
│   ├── live_scraper.py       # Live session scraper
│   ├── mockair_scraper.py    # MockAir network scraper (sandbox)
│   ├── amadeus_client.py     # Amadeus API client (secondary)
│   ├── ignav_client.py       # IgNav client (deprecated, alias)
│   ├── base.py               # Fare collector base class
│   └── db_retry.py           # Database retry wrapper
│
├── index/
│   ├── calculator.py         # Jevons / Carli / Dutot / Laspeyres / Tornqvist index computation
│   ├── formulas.py           # Index formula implementations
│   └── heatmap.py            # Sector x horizon heatmap computation
│
├── validation/
│   ├── backtest.py           # 30-day DGCA backtest (Pearson r, RMSE, MAPE)
│   └── evaluator.py          # CPI benchmark tracking evaluation
│
├── analytics/
│   └── enterprise_intelligence.py  # Volatility metrics, fair-price forecast
│
├── pipeline/
│   ├── scheduler.py          # Background ingestion daemon
│   └── governance.py         # Outlier review and imputation lineage
│
├── data/
│   ├── db.py                 # SQLite schema, connection helpers, all DB queries
│   ├── routes.json           # Corridor definitions, airport coordinates, basket weights
│   └── scheduler_state.json  # Scheduler persistence state
│
├── src/rapa/ingestion/
│   ├── custom_scraper.py     # RAPAStealthEngine + ProxyRotator (Phase 1)
│   └── dynamic_session_engine.py  # Playwright dynamic DOM engine (Phase 2)
│
├── portal/
│   └── index.html            # Web portal HTML (served at /portal/index.html)
│
├── dashboard/
│   └── app.py                # Streamlit dashboard (alternative UI)
│
├── scripts/
│   ├── audit_pure.py
│   ├── sync_mockair_to_flight_quotes.py
│   ├── test_ignav_coverage.py
│   └── verify_live_mockair_scraper.py
│
├── tests/                    # Full pytest test suite (13 modules)
│   ├── test_api.py
│   ├── test_benchmark.py
│   ├── test_formulas.py
│   ├── test_heatmap_backtest.py
│   ├── test_scheduler.py
│   └── ...
│
├── raw_dumps/                # Raw scraped HTML/JSON dumps (auto-generated)
├── logs/                     # Rotating server logs (auto-generated)
│
├── processor.py              # Gemini Flash parsing pipeline (Phase 3)
├── db_setup.py               # One-time database initialization
├── schema.py                 # Database schema definitions
└── scheduler.py              # Top-level scheduler wrapper
```

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/savanthkumarvedesh-code/rapa-engine.git
cd rapa-engine

# Create a virtual environment
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — macOS / Linux
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` and configure:

```env
# MoSPI eSankhyiki API (required for CPI benchmark ingestion)
MOSPI_API_KEY=your_key_here

# Google Gemini API (required for Phase 3 HTML parsing pipeline)
GEMINI_API_KEY=your_key_here

# Optional: Proxy pool for stealth scraper (comma-separated)
# RAPA_PROXIES=http://ip1:port,http://ip2:port
```

---

## Running the Application

All commands go through the unified CLI at `run.py`.

### Start the Web Portal and API

```bash
python run.py api
```

- Web portal: `http://localhost:8000` or `http://localhost:8000/portal/index.html`
- Swagger API docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Ingest Official MoSPI CPI Benchmark Data

```bash
python run.py ingest
```

Fetches CPI Item 294 Airfare records (Base 2024=100) and Group 07.3 Transport Proxy (Base 2012=100) from the official MoSPI eSankhyiki API and stores them in SQLite.

### Collect Live Fare Quotes

```bash
# Phase 1 — Static stealth scraper (raw HTML dumps)
python run.py scrape

# Phase 2 — Dynamic session engine (Playwright DOM capture)
python run.py dynamic-scrape

# OTA portal scraper (MMT, Goibibo, Cleartrip, Ixigo, EaseMyTrip, Yatra)
python run.py scrape-ota

# Phase 3 — Parse raw HTML dumps into structured records via Gemini Flash
python run.py parse-dumps

# Batch fare collection + index computation in one step
python run.py fetch-fares
```

### Run a Full Pipeline Cycle

```bash
python run.py cycle
```

Runs: MoSPI ingest, live fare collection, and CPI benchmark tracking evaluation in sequence.

### Background Scheduler Daemon

```bash
# Start the automated ingestion daemon (interval in seconds)
python run.py daemon 300

# Or via the top-level scheduler
python run.py schedule-start
python run.py schedule-status
python run.py schedule-trigger
```

### Streamlit Dashboard (Alternative UI)

```bash
python run.py dashboard
# Available at http://localhost:8501
```

### System Status Check

```bash
python run.py status
```

### Run Tests

```bash
python run.py test
```

---

## API Reference

Full interactive documentation is available at `http://localhost:8000/docs` after starting the server.

### Endpoint Groups

| Group | Base Path | Description |
|-------|-----------|-------------|
| System | `/v1/health` | Health check and database telemetry |
| CPI Benchmark | `/v1/benchmark/*` | MoSPI eSankhyiki Item 294 Airfare records |
| Real-Time Fares | `/v1/fares/*` | Route-level fare microdata and collector status |
| Computed Index | `/v1/index/*` | Jevons / multi-formula price index series |
| Benchmark Validation | `/v1/validation/*` | CPI calibration and DGCA 30-day backtest |
| Sector Heatmaps | `/v1/heatmap/*` | 2D sector x horizon fare heatmaps |
| NSO / RBI Feed | `/v1/nso-rbi/*` | SDMX-aligned machine-readable index feed |
| Analytics | `/v1/analytics/*` | Volatility metrics and fair-price forecast |
| Statistical Governance | `/v1/governance/*` | Outlier review, health matrix, audit lineage |
| Geographic Routes | `/v1/routes/*` | Airport coordinates and corridor proximity matrix |
| Export Engine | `/v1/export/*` | CSV and JSON export for all datasets |
| Scheduler | `/v1/scheduler/*` | Background daemon control (start, stop, trigger) |

---

## Index Methodology

### National Airfare Index (NAI)

The headline index is computed as a **Matched-Item Jevons Geometric Mean** across all monitored corridors:

```
NAI = EXP( SUM( w_i * LN(P_i / P0_i) ) ) * 100
```

Where:
- `P_i` = current average fare for corridor i
- `P0_i` = baseline average fare for corridor i (December 2025)
- `w_i` = DGCA basket weight for corridor i (sums to 1.0)

The Jevons formula eliminates substitution bias — a statistically significant distortion of approximately 2.13 index points compared to arithmetic averaging methods.

### Validation Against MoSPI CPI

Calibration against MoSPI Official CPI Item 294 (Airfare, Base 2024=100) uses:
- Pearson correlation coefficient (r) over a 30-day rolling window
- Root Mean Squared Error (RMSE) in index points
- Mean Absolute Percentage Error (MAPE)

### Dynamic Surge Premium

```
Surge Premium % = ((T+1 Avg Fare - T+45 Avg Fare) / T+45 Avg Fare) * 100
```

Measures the price premium paid by passengers booking 1 day ahead versus 45 days ahead on the same corridor.

---

## SIH Context

| Field | Value |
|-------|-------|
| Hackathon | Smart India Hackathon (SIH) |
| Problem Domain | Ministry of Statistics and Programme Implementation (MoSPI) |
| Objective | Augment India CPI transport basket with high-frequency real-time airfare data |
| Target Beneficiary | NSO / RBI macro-modeling pipelines |
| Data Dissemination Standard | SDMX-aligned JSON micro-index feed |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'feat: add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

This project is submitted as part of Smart India Hackathon and is intended for academic and research use.

---

## Repository

[github.com/savanthkumarvedesh-code/rapa-engine](https://github.com/savanthkumarvedesh-code/rapa-engine)
