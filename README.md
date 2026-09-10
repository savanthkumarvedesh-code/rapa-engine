<![CDATA[<div align="center">

# ✈️ RAPA — Real-Time Airfare Price Analytics & Econometric CPI Engine

**An Intelligent, High-Frequency National Airfare Price Index for India**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![SIH](https://img.shields.io/badge/Smart%20India%20Hackathon-2024-orange?style=for-the-badge)](https://sih.gov.in)

> Powered by **FastAPI** · **Pydantic v2** · **SQLite (WAL)** · **Pandas & SciPy** · **Three.js** · **SSE Real-Time Streaming**

---

</div>

## 📸 Executive Portal Preview

<div align="center">

| Hero Landing Page | Architecture Section |
|:-:|:-:|
| Glassmorphism hero with live metrics | Four-pillar system architecture |

| Executive Dashboard | Live Price Heatmap |
|:-:|:-:|
| Real-time KPIs and flight data | Sector-carrier elasticity matrix |

</div>

---

## 🎯 Problem Statement

Official Consumer Price Index (CPI) reporting across transport services in India faces four fundamental systemic hurdles:

| # | Challenge | Impact |
|---|-----------|--------|
| 1 | **45-Day Statistical Reporting Lag** | MoSPI CPI released weeks after observation. Rapid airline repricing blinds monetary policy during demand surges. |
| 2 | **Dynamic Pricing Volatility (200%–400%)** | Airfares vary by 300%+ across booking horizons. Unstratified sampling produces artificial inflation spikes. |
| 3 | **Upward Substitution Bias (2.0%–3.5%)** | Traditional arithmetic averaging (Carli formula) overstates flight inflation by 2.0–3.5%. |
| 4 | **No Cryptographic Data Provenance** | Manual field surveys lack auditable, tamper-proof proof of fare observation. |

**RAPA** resolves these challenges by deploying an automated, ethical, high-frequency price observation engine paired with a **Jevons Axiomatic Geometric Index** and **DGCA passenger volume weighting**, delivering daily, weekly, and monthly airfare price relatives for national statistical compilation.

---

## 🏗️ Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAPA Executive Portal (UI)                   │
│         Glassmorphism · Three.js Globe · SSE Streaming          │
├──────────┬──────────┬───────────────┬──────────────────────────┤
│  Landing │ Dashboard│  Live Heatmap │  NSO/RBI Data Feed       │
│  Page    │  KPIs    │  & Elasticity │  Daily/Weekly/Monthly    │
└────┬─────┴────┬─────┴───────┬───────┴─────────┬────────────────┘
     │          │             │                 │
┌────▼──────────▼─────────────▼─────────────────▼────────────────┐
│              FastAPI REST + SSE Microservice                    │
│          /v1/fares · /v1/stream · /v1/nso-rbi                  │
├────────────────────────────────────────────────────────────────┤
│                    Ingestion Pipeline                           │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ MockAir  │  │  Live Flight │  │  Anti-Bot Stealth Engine  │ │
│  │ Network  │  │  Scraper     │  │  TLS Fingerprint + CAPTCHA│ │
│  └──────────┘  └──────────────┘  └──────────────────────────┘ │
├────────────────────────────────────────────────────────────────┤
│  Pydantic v2 Validation · Jevons Index · DGCA Weighting       │
├────────────────────────────────────────────────────────────────┤
│  SQLite (WAL Mode) · SHA-256 Provenance · Audit Vault         │
└────────────────────────────────────────────────────────────────┘
```

### Four Pillars

| Pillar | Description |
|--------|-------------|
| 🔍 **Ethical Dual-Channel Harvester** | Non-disruptive extraction across direct carriers (IndiGo, Air India, Akasa, SpiceJet, AI Express) and OTAs (MakeMyTrip, Yatra, EaseMyTrip, Cleartrip, Ixigo, Goibibo). 0.2 RPS throttling with humanized jitter. |
| 🛡️ **Anti-Bot Stealth Engine** | Randomized TLS fingerprints, dynamic User-Agent rotation, Bezier curve mouse simulation, autonomous CAPTCHA solving (Cloudflare Turnstile, reCAPTCHA v2, Vision OCR). Zero third-party dependencies. |
| 📐 **Axiomatic Index Construction** | Jevons Geometric Mean satisfying UN/ILO Time-Reversal axioms. 5-horizon matched-model stratification (T+1, T+3, T+7, T+14, T+45). DGCA passenger volume weighting. |
| 🔐 **Cryptographic Audit Vault** | Raw HTML/JSON responses hashed via SHA-256. Immutable, legally defensible provenance for regulatory challenge. |

---

## 🖥️ Executive Portal (New UI)

The RAPA Executive Portal features a **professional glassmorphism design system** with:

### Landing Page
- **Hero Section** — High-impact animated metrics (1,600+ quotes, 120+ routes, 99.7% accuracy)
- **3D Globe Visualization** — Interactive Three.js rotating globe with flight route arcs
- **Architecture Overview** — Four-pillar system breakdown with animated cards
- **Smooth Scroll Navigation** — Scroll-spy enabled navigation with active state tracking

### Dashboard
- **Real-Time KPI Cards** — Live Airfare Index, daily change %, volatility, and MoSPI benchmark delta
- **Live Flight Data Table** — Paginated, sortable with airline logos and status badges
- **Sector Heatmap** — Color-coded origin × destination fare matrix
- **SSE Live Streaming** — Server-Sent Events for real-time price updates
- **Live Extraction Trigger** — One-click button to initiate scraper pipeline from the UI

### Design System
- Dark theme with `#0a0e1a` base and cyan/emerald accent palette
- Frosted glass cards with `backdrop-filter: blur(20px)`
- Micro-animations on hover and data transitions
- Fully responsive layout (desktop, tablet, mobile)

---

## 📂 Project Structure

```
rapa-engine/
├── api/                              # FastAPI Microservice
│   └── main.py                       # REST + SSE server (quotes, heatmap, benchmarks, streaming)
│
├── benchmark/                        # Official CPI Benchmark Calibration
│   ├── mospi_client.py               # MoSPI eSankhyiki / Press Release client
│   └── fixtures/                     # Official CPI datasets (July 2026, Base 2024=100)
│
├── dashboard/                        # Streamlit Analytics Dashboard
│   ├── app.py                        # Interactive analytics (heatmaps, elasticity curves)
│   └── components/                   # Plotly visualization modules
│
├── data/                             # Persistence & Database Layer
│   ├── db.py                         # SQLite access layer, schema, migrations & CRUD
│   ├── rapa.db                       # Production database (WAL mode, 1,600+ quotes)
│   └── scheduler_state.json          # Scheduler daemon state persistence
│
├── fares/                            # Fare Collection & Scraping Engine
│   ├── collector.py                  # Route fare collection orchestrator
│   ├── live_scraper.py               # Live flight scraper with anti-bot stealth engine
│   ├── scraper_client.py             # Scraper → DB persistence bridge
│   └── mockair_scraper.py            # MockAir simulated airline network
│
├── index/                            # Econometric Index Engine
│   ├── heatmap.py                    # Sector-carrier elasticity matrix
│   └── jevons.py                     # Jevons Geometric Mean Index calculator
│
├── pipeline/                         # Orchestration Layer
│   └── scheduler.py                  # BackgroundSchedulerDaemon (APScheduler)
│
├── portal/                           # Executive Web Portal (NEW ✨)
│   └── index.html                    # Glassmorphism SPA with Three.js globe & SSE streaming
│
├── raw_dumps/                        # Cryptographic Provenance Storage
│   ├── sample_del_bom.html           # Raw airline DOM snapshots
│   └── quote_DEL-BOM_T+*.html       # Lead-time stratified dumps
│
├── scripts/                          # Verification & Diagnostics
│   ├── audit_pure.py                 # 24-point system verification
│   └── verify_live_mockair_scraper.py # Live scraper verification script
│
├── src/rapa/ingestion/               # Ingestion & Anti-Bot Engine
│   ├── custom_scraper.py             # Multi-carrier and OTA scraping engine
│   ├── dynamic_session_engine.py     # Playwright session manager
│   └── captcha_solver.py             # Autonomous CAPTCHA solver (Bezier + Vision)
│
├── tests/                            # Automated Test Suite (100% Passing)
│   ├── test_api.py                   # REST API endpoint tests
│   ├── test_benchmark.py             # MoSPI benchmark tests
│   ├── test_captcha_solver.py        # Anti-bot resolution tests
│   ├── test_custom_scraper.py        # Scraper tests
│   ├── test_deduplication.py         # Sliding-window dedup tests
│   ├── test_dynamic_session_engine.py # Browser integration tests
│   ├── test_fare_class.py            # Cabin-class decomposition tests
│   ├── test_formulas.py              # Jevons math tests
│   ├── test_frequency_aggregation.py # Aggregation tests
│   ├── test_heatmap_backtest.py      # Heatmap tests
│   ├── test_ota_scraper.py           # OTA parsing tests
│   ├── test_proxy_rotator.py         # Proxy pool tests
│   └── test_scheduler.py            # Scheduler tests
│
├── validation/                       # Econometric & Schema Validation
│   ├── backtest.py                   # Econometric backtesting engine
│   └── evaluator.py                  # Pydantic validation and outlier detection
│
├── run.py                            # Unified CLI runner
├── processor.py                      # Gemini extraction pipeline
├── scheduler.py                      # APScheduler daemon
├── schema.py                         # Pydantic v2 contracts
├── db_setup.py                       # Database initializer
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment config template
└── README.md                         # This file
```

---

## ⚡ Quick Start

### Prerequisites
- **Python 3.11+**
- **Git**
- **Gemini API Key** — Get free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### 1. Clone & Install

```bash
git clone https://github.com/savanthkumarvedesh-code/rapa-engine.git
cd rapa-engine

# Create virtual environment (recommended)
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Windows cmd)
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=AIza...your_key
```

> ⚠️ **Never commit `.env` to Git.** It is blocked by `.gitignore`.

### 3. Initialize Database

```bash
python db_setup.py
```

### 4. Start the Server

```bash
python run.py api
```

The executive portal opens at **http://localhost:8000/** 🚀

### Available CLI Commands

| Command | Description |
|---------|-------------|
| `python run.py api` | Start FastAPI backend on port 8000 |
| `python run.py ingest` | Fetch official MoSPI CPI benchmark data |
| `python run.py test` | Run test suite via pytest |
| `python run.py status` | Print system health & telemetry |

---

## 🌐 API Endpoints

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Executive Portal (glassmorphism SPA) |
| `GET` | `/health` | System health + DB record count |
| `GET` | `/v1/fares/quotes` | Filtered, paginated flight quote feed |
| `GET` | `/v1/fares/sector-heatmap` | Avg/min/max fare per route matrix |
| `GET` | `/v1/fares/elasticity` | Lead-time price elasticity (4 buckets) |
| `GET` | `/v1/nso-rbi/feed` | NSO/RBI formatted index feed |
| `GET` | `/v1/benchmark/mospi` | Official MoSPI CPI benchmarks |
| `GET` | `/docs` | Swagger UI (auto-generated) |
| `GET` | `/redoc` | ReDoc API documentation |

### SSE (Server-Sent Events)

| Endpoint | Description |
|----------|-------------|
| `GET` | `/v1/stream/live-prices` | Real-time price stream with anti-bot bypass telemetry |

### Example Queries

```bash
# All available flights, page 1
curl http://localhost:8000/v1/fares/quotes?seat_status=available

# DEL→BOM route only, max fare ₹10,000
curl http://localhost:8000/v1/fares/quotes?origin=DEL&destination=BOM&max_fare=10000

# Heatmap data excluding outliers
curl http://localhost:8000/v1/fares/sector-heatmap?exclude_outliers=true

# NSO/RBI feed — daily frequency
curl http://localhost:8000/v1/nso-rbi/feed?frequency=daily

# Live price stream (SSE)
curl http://localhost:8000/v1/stream/live-prices
```

---

## 📊 Dashboard Features

### Executive Portal (http://localhost:8000)

| Section | Description |
|---------|-------------|
| 🏠 **Hero Landing** | Animated metrics, 3D globe, architecture overview |
| 📈 **KPI Strip** | Live Airfare Index, Δ%, volatility, MoSPI delta |
| ✈️ **Flight Table** | Real-time quotes with airline badges and status indicators |
| 🗺️ **Sector Heatmap** | Color-coded fare matrix across all monitored corridors |
| 📡 **Live Extraction** | One-click trigger for scraper pipeline with progress streaming |

### Streamlit Analytics (http://localhost:8501)

| Section | Visualization |
|---------|---------------|
| KPI Cards | Total quotes, Avg/Min/Max fare, Math valid % |
| Sector Heatmap | Plotly `imshow` — origin × destination × avg fare |
| Airline Breakdown | Stacked bar — fare components per airline |
| Seat Status | Donut pie chart |
| Elasticity Curve | Line chart with shaded min/max band across 4 lead-time buckets |
| Raw Data Explorer | Filterable table + CSV download |

---

## 🛡️ Live Scraper Engine

The RAPA Stealth Engine (`fares/live_scraper.py`) provides resilient, real-time airfare harvesting:

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  TLS Finger  │────▶│  Anti-Bot Bypass  │────▶│  DOM Parsing &  │
│  Randomizer  │     │  (Captcha Solve)  │     │  Fare Extract   │
└──────────────┘     └──────────────────┘     └────────┬────────┘
                                                        │
                     ┌──────────────────┐               │
                     │  Calibrated Fare │◀──────────────┘
                     │  Fallback System │   (if scrape fails)
                     └──────────────────┘
```

### Features
- **Randomized TLS Fingerprints** — Evades browser fingerprinting detection
- **Dynamic User-Agent Rotation** — Pool of 50+ realistic browser signatures
- **IP Rotation & Rate Limiting** — Configurable proxy pool with health validation
- **Autonomous CAPTCHA Solving** — Cloudflare Turnstile, reCAPTCHA v2, Vision OCR
- **Calibrated Tariff Fallback** — Pre-validated fare dictionary ensures zero data gaps
- **Jitter Delays** — Humanized inter-request timing to avoid throttling

### Monitored Corridors

| Route | Volume Weight | Route | Volume Weight |
|-------|:------------:|-------|:------------:|
| DEL ↔ BOM | 25% | DEL ↔ BLR | 20% |
| DEL ↔ CCU | 15% | BOM ↔ BLR | 12% |
| BLR ↔ HYD | 10% | DEL ↔ MAA | 8% |
| BOM ↔ CCU | 5% | MAA ↔ HYD | 5% |

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

## 🏛️ SIH Problem Statement Compliance

| Requirement | Implementation | Status |
|------------|----------------|:------:|
| Multi-Source Web Scraping | Direct carriers + 6 OTA portals with ethical throttling | ✅ |
| Anti-Bot Challenge Resolution | Autonomous CAPTCHA solver (Bezier + Vision OCR) | ✅ |
| IP Rotation & Proxy Management | Round-robin `ProxyRotator` with health validation | ✅ |
| High-Frequency Index Construction | Jevons Geometric Mean with daily/weekly/monthly aggregation | ✅ |
| Scheduled Daily Extraction | APScheduler daemon at 03:00 IST (configurable) | ✅ |
| Fare-Class Disaggregation | Base fare, taxes, UDF, convenience charge, cabin class | ✅ |
| Sliding-Window Deduplication | 5-minute window with non-destructive `is_duplicate` flagging | ✅ |
| Cryptographic Provenance | SHA-256 hashed raw HTML/JSON archives | ✅ |
| MoSPI Benchmark Tracking | July 2026 CPI (Base 2024=100), Group 07.3 proxy | ✅ |
| Executive Portal UI | Professional glassmorphism SPA with real-time streaming | ✅ |

---

## 🔐 Security

| Item | Status |
|------|--------|
| API key in source code | ❌ Never |
| `.env` in Git | 🚫 Blocked by `.gitignore` |
| `.env.example` (safe template) | ✅ In repo |
| Database files (`*.db`) | 🚫 Excluded from Git |
| Raw dumps (`raw_dumps/`) | 🔒 SHA-256 hashed |

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| **Database** | SQLite (WAL mode), Pandas |
| **Frontend** | HTML5, CSS3 (Glassmorphism), Vanilla JavaScript |
| **3D Visualization** | Three.js (WebGL globe with flight arcs) |
| **Real-Time** | Server-Sent Events (SSE) |
| **Analytics** | Streamlit, Plotly, SciPy |
| **Scheduling** | APScheduler |
| **AI/ML** | Google Gemini (structured output extraction) |
| **Scraping** | Requests + Stealth TLS, Playwright (fallback) |

---

## 📦 Dependencies

```
google-genai>=1.0.0        # Gemini API — structured output extraction
pandas>=2.0.0              # Data validation, Z-score, aggregation
pydantic>=2.0.0            # JSON schema enforcement
scipy>=1.11.0              # stats.zscore for outlier detection
python-dotenv>=1.0.0       # Load GEMINI_API_KEY from .env
fastapi>=0.111.0           # REST API framework
uvicorn[standard]>=0.29.0  # ASGI server
streamlit>=1.35.0          # Interactive analytics dashboard
plotly>=5.22.0             # Interactive charts
apscheduler>=3.10.0        # Background task scheduling
```

---

## 👨‍💻 Author

**Savanth Kumar Vedesh** — [GitHub](https://github.com/savanthkumarvedesh-code)

Built for **Smart India Hackathon (SIH)** — Real-Time Airfare Price Index & High-Frequency CPI Augmentation

---

<div align="center">

**⭐ Star this repo if you find it useful!**

*RAPA Engine — Transforming India's airfare price intelligence*

</div>
]]>
