# ✈️ RAPA Engine — Flight Quote Ingestion Pipeline

A production-grade data pipeline that ingests raw HTML/JSON flight-quote dumps,
extracts structured records via **Google Gemini Structured Outputs**, validates
the pricing mathematics and flags price outliers using **Pandas + SciPy Z-scores**,
then persists everything to a **SQLite** database.

---

## 📁 Project Layout

```
flight_ingestion_pipeline/
├── raw_dumps/                  ← Drop your HTML/JSON dump files here
│   ├── sample_del_bom.html     ← Sample HTML (5 flights, 1 outlier)
│   └── sample_maa_hyd.json     ← Sample JSON (3 flights)
├── schema.py                   ← Pydantic v2 models (Gemini output contract)
├── db_setup.py                 ← SQLite schema initialiser
├── processor.py                ← Main pipeline (Extract → Validate → Persist)
├── requirements.txt            ← Python dependencies
└── README.md                   ← You are here
```

---

## ⚙️ Step 1 — Environment Setup

### 1a. Python Version
Requires **Python 3.11+** (for `X | Y` union syntax and `match` statements).

```powershell
python --version
```

### 1b. Install Dependencies

> **sqlite3** is part of Python's standard library — no separate install needed.

```powershell
# Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell

# Install pipeline dependencies
pip install -r requirements.txt
```

The packages installed are:
| Package | Purpose |
|---|---|
| `google-genai` | Official Gemini Python SDK (structured outputs) |
| `pandas` | DataFrame operations, math validation |
| `pydantic` | JSON schema enforcement / runtime validation |
| `scipy` | `scipy.stats.zscore` for outlier detection |

### 1c. Set your Gemini API Key

Get a free key at → https://aistudio.google.com/apikey

```powershell
# Windows PowerShell (current session)
$env:GEMINI_API_KEY = "AIza..."

# Windows PowerShell (permanent — current user)
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "AIza...", "User")

# Linux / macOS
export GEMINI_API_KEY="AIza..."
```

> ⚠️ **Never commit your API key to Git.** Use environment variables or a `.env` file
> added to `.gitignore`.

---

## 🗄️ Step 2 — Initialise the Database

Run this **once** before your first pipeline execution:

```powershell
python db_setup.py
```

Expected output:
```
[db_setup] Database ready → C:\...\flight_quotes.db
[db_setup] Table 'flight_quotes' created/verified at: C:\...\flight_quotes.db
```

This is safe to re-run — it uses `CREATE TABLE IF NOT EXISTS` and will never
delete existing data.

---

## 🚀 Step 3 — Run the Pipeline

```powershell
# Default: reads from ./raw_dumps/, writes to ./flight_quotes.db
python processor.py

# Custom paths
python processor.py --dumps ./my_dumps --db ./custom.db
```

### What happens internally

```
STAGE 1  DISCOVER   Scan raw_dumps/ for .html, .json, .txt, .xml files
    ↓
STAGE 2  EXTRACT    Per file → call Gemini (gemini-2.5-flash) with Structured Output
                    Returns FlightQuoteList validated by Pydantic
    ↓
STAGE 3  VALIDATE   Math check: total_fare = base + taxes + UDF + conv (±0.01)
                    Outlier flag: |Z-score| > 3.0 on total_fare across the batch
    ↓
STAGE 4  PERSIST    pandas.to_sql() → INSERT INTO flight_quotes (append mode)
```

### Sample output

```
2026-10-15 10:30:01 [INFO] Database ready → flight_quotes.db
2026-10-15 10:30:01 [INFO] Discovered 2 file(s) in raw_dumps
2026-10-15 10:30:02 [INFO] Extracting → sample_del_bom.html
2026-10-15 10:30:05 [INFO]   → Extracted 5 quote(s)
2026-10-15 10:30:05 [INFO] Extracting → sample_maa_hyd.json
2026-10-15 10:30:07 [INFO]   → Extracted 3 quote(s)
2026-10-15 10:30:07 [INFO] Total quotes extracted across all files: 8
2026-10-15 10:30:07 [INFO] --- Running Validation ---
2026-10-15 10:30:07 [INFO] Math validation passed for all 8 record(s).
2026-10-15 10:30:07 [WARNING] 1 price outlier(s) detected (|z| > 3.0):
2026-10-15 10:30:07 [WARNING]   Flight UK 935 | total_fare=33500.00 | z=3.62
2026-10-15 10:30:07 [INFO] Inserted 8 record(s) into flight_quotes.db → flight_quotes
2026-10-15 10:30:07 [INFO] Pipeline complete. Database: flight_quotes.db
```

---

## 🔍 Step 4 — Query the Database

```powershell
# Open SQLite3 shell
sqlite3 flight_quotes.db
```

```sql
-- View all records
SELECT id, flight_number, airline, total_fare, is_math_valid, is_price_outlier
FROM flight_quotes;

-- Find price outliers
SELECT flight_number, airline, total_fare
FROM flight_quotes
WHERE is_price_outlier = 1;

-- Find records with invalid maths
SELECT flight_number, base_fare, taxes, user_development_fee,
       convenience_charge, total_fare
FROM flight_quotes
WHERE is_math_valid = 0;

-- Summary statistics per airline
SELECT airline, COUNT(*) as flights, AVG(total_fare) as avg_fare
FROM flight_quotes
GROUP BY airline
ORDER BY avg_fare DESC;
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
    seat_status          TEXT    NOT NULL CHECK (seat_status IN ('available','sold-out','cancelled')),
    is_math_valid        INTEGER NOT NULL DEFAULT 1,
    is_price_outlier     INTEGER NOT NULL DEFAULT 0,
    source_file          TEXT,
    ingestion_timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔗 Integrating with the rapa-engine Repository

> **Note:** The repository `https://github.com/savanthkumarvedesh-code/rapa-engine.git`
> returned a 404 during setup (it may be private or the URL may be incorrect).
>
> Once you have access, integrate with:

```powershell
cd C:\path\to\rapa-engine
# Copy pipeline files
Copy-Item ..\flight_ingestion_pipeline\*.py .
Copy-Item ..\flight_ingestion_pipeline\requirements.txt .
Copy-Item ..\flight_ingestion_pipeline\raw_dumps\ .\raw_dumps\ -Recurse

git add .
git commit -m "feat: add Gemini-powered flight quote ingestion pipeline"
git push
```

---

## 🛡️ Model Note

> You requested `gemini-3.6-flash`. That model ID does not exist at the time of
> writing. The pipeline uses `gemini-2.5-flash` (current recommended fast model).
> To switch models, edit `MODEL_ID` at the top of `processor.py`.
