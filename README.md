# ✈️ RAPA Engine — Flight Quote Ingestion & Analytics Platform

> Powered by **Google Gemini 3.6 Flash** | FastAPI | Streamlit | SQLite | Pandas

A production-grade, end-to-end flight quote data platform:
- **Ingests** raw HTML/JSON dumps scraped from booking portals
- **Extracts** structured records using Gemini 3.6 Flash (AI-powered parsing)
- **Validates** fare mathematics and detects price outliers with Z-scores
- **Serves** data via a government-ready REST API (FastAPI)
- **Visualises** sector heatmaps and lead-time elasticity via a Streamlit dashboard

---

## 📁 Project Structure

```
rapa-engine/
├── raw_dumps/                        ← Drop raw HTML/JSON dump files here
│   ├── sample_del_bom.html           ← Sample: 5 flights DEL→BOM (incl. outlier)
│   ├── sample_maa_hyd.json           ← Sample: 3 flights MAA→HYD
│   └── quote_DEL-BOM_T+*.html        ← Lead-time variant dumps (T+1, T+7, T+15...)
│
├── schema.py          ← Pydantic v2 structured output contract for Gemini
├── db_setup.py        ← SQLite schema initialiser (flight_quotes.db)
├── processor.py       ← Phase 1: Gemini extraction + validation + ingestion
├── main.py            ← Phase 2: FastAPI REST service (3 endpoints + health)
├── dashboard.py       ← Phase 2: Streamlit analytics dashboard
├── api_test.py        ← Gemini API connectivity diagnostic
├── query_db.py        ← SQLite database inspector + fare stats
│
├── src/rapa/ingestion/
│   ├── custom_scraper.py         ← Custom HTML scraper engine
│   └── dynamic_session_engine.py ← Dynamic session-based scraper
├── tests/
│   ├── test_custom_scraper.py
│   └── test_dynamic_session_engine.py
│
├── requirements.txt   ← All Python dependencies
├── .env.example       ← API key template (copy to .env — never commit .env)
├── .gitignore         ← Blocks .env, *.db, __pycache__ from Git
└── README.md
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
    source_file          TEXT,
    ingestion_timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

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

| File | Phase | Purpose |
|---|---|---|
| `schema.py` | 1 | Pydantic v2 Gemini output contract |
| `db_setup.py` | 1 | SQLite schema initialiser |
| `processor.py` | 1 | Ingestion pipeline (Discover→Extract→Validate→Persist) |
| `main.py` | 2 | FastAPI REST service |
| `dashboard.py` | 2 | Streamlit analytics dashboard |
| `api_test.py` | - | Gemini API connectivity diagnostic |
| `query_db.py` | - | Database inspector |
| `requirements.txt` | - | All dependencies |
| `.env.example` | - | API key template |
| `.gitignore` | - | Secrets + generated files protection |
