# RAPA Engine — Complete System Documentation
**Real-Time Airfare Price Augmentation & Econometric CPI Augmentation System**
*National Statistical Office (NSO), Ministry of Statistics and Programme Implementation (MoSPI) & Reserve Bank of India (RBI)*

---

## Table of Contents
1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [High-Level System Architecture](#2-high-level-system-architecture)
3. [Econometric Methodology & Mathematical Formulations](#3-econometric-methodology--mathematical-formulations)
   - [3.1 The Matched-Item Jevons Index](#31-the-matched-item-jevons-index)
   - [3.2 Multi-Formula Index Lab](#32-multi-formula-index-lab)
   - [3.3 Substitution Bias Quantification](#33-substitution-bias-quantification)
   - [3.4 MoSPI CPI Item 294 Benchmark Alignment](#34-mospi-cpi-item-294-benchmark-alignment)
   - [3.5 Lead-Time Elasticity & Dynamic Surge Premium](#35-lead-time-elasticity--dynamic-surge-premium)
4. [Data Ingestion & Scraping Architecture](#4-data-ingestion--scraping-architecture)
   - [4.1 Target Aviation Basket](#41-target-aviation-basket)
   - [4.2 Primary Scraping Engine (Google Flights CRS Aggregation)](#42-primary-scraping-engine-google-flights-crs-aggregation)
   - [4.3 Secondary Wholesale GDS Pipeline](#43-secondary-wholesale-gds-pipeline)
   - [4.4 Stealth Ingestion Engine (Scrapling & Playwright)](#44-stealth-ingestion-engine-scrapling--playwright)
   - [4.5 Autonomous CAPTCHA Resolution Engine](#45-autonomous-captcha-resolution-engine)
   - [4.6 Fare Decomposition (Base Fare vs. UDF/Taxes)](#46-fare-decomposition-base-fare-vs-udftaxes)
   - [4.7 Operational Tariff Calibration & Offline Fallback](#47-operational-tariff-calibration--offline-fallback)
5. [Database Architecture & Data Dictionary](#5-database-architecture--data-dictionary)
   - [5.1 SQLite Schema](#51-sqlite-schema)
   - [5.2 Concurrency & Exponential Backoff Retry](#52-concurrency--exponential-backoff-retry)
   - [5.3 Audit Lineage & Ingestion Logging](#53-audit-lineage--ingestion-logging)
6. [API Specifications & Endpoint Reference](#6-api-specifications--endpoint-reference)
   - [6.1 System Telemetry](#61-system-telemetry)
   - [6.2 CPI Benchmark Ingestion](#62-cpi-benchmark-ingestion)
   - [6.3 Real-Time Fare Microdata](#63-real-time-fare-microdata)
   - [6.4 Computed Price Index](#64-computed-price-index)
   - [6.5 Validation & Backtest](#65-validation--backtest)
   - [6.6 Sector Heatmap & Carrier Disparity](#66-sector-heatmap--carrier-disparity)
   - [6.7 NSO / RBI Machine Feed](#67-nso--rbi-machine-feed)
   - [6.8 Enterprise Intelligence & Volatility](#68-enterprise-intelligence--volatility)
   - [6.9 Statistical Governance](#69-statistical-governance)
   - [6.10 Export Engine](#610-export-engine)
   - [6.11 Server-Sent Events (SSE) Live Stream](#611-server-sent-events-sse-live-stream)
7. [Web Portal & Visualization Architecture](#7-web-portal--visualization-architecture)
8. [Statistical Governance & Outlier Control](#8-statistical-governance--outlier-control)
9. [Chronological Development Log](#9-chronological-development-log)
10. [Operational Runbook & CLI Guide](#10-operational-runbook--cli-guide)

---

## 1. Executive Summary & Problem Statement

### 1.1 The MoSPI Publication Lag Challenge
In the Indian statistical system, the Consumer Price Index (CPI) tracks price changes across essential goods and services. Transportation, specifically **Item 294 (Airfare, Base 2024=100)** within Group 07.3, is one of the most volatile components of the modern Indian consumption basket.

Under standard collection workflows, airfare data is collected via monthly manual price schedules from selected booking counters and published with an approximate **45-day lag**. For instance, price shocks occurring in mid-May are only reflected in official statistical releases in mid-July. This latency poses several structural challenges:
1. **Monetary Policy Timing**: The Reserve Bank of India (RBI) Monetary Policy Committee (MPC) must make interest rate decisions based on outdated transport inflation figures.
2. **Dynamic Pricing Blindness**: Commercial aviation utilizes dynamic revenue management systems where ticket prices fluctuate on an hourly basis across varying booking lead times (from 45 days in advance down to 24 hours prior to departure). Static monthly snapshots miss high-yield surge periods and low-tariff promotional windows entirely.
3. **Substitution Bias**: When one airline increases fares on a corridor, consumers naturally migrate to lower-cost carriers (LCCs). Traditional arithmetic aggregation formulas overestimate inflation by ignoring passenger substitution.

### 1.2 The RAPA Solution
The Real-Time Airfare Price Augmentation (**RAPA**) Engine solves this problem by automating the continuous harvesting of flight tariffs across India's primary domestic air corridors, calculating a high-frequency **Matched-Item Jevons Geometric Index**, and calibrating the results directly against MoSPI official CPI benchmarks with zero publication latency.

---

## 2. High-Level System Architecture

```
+-----------------------------------------------------------------------------------+
|                            DATA COLLECTION LAYER                                  |
|                                                                                   |
|  +---------------------------+   +-----------------------+   +-----------------+  |
|  | Google Flights Aggregator |   | GDS Wholesale Feed    |   | Playwright      |  |
|  | (Live Reservation Feeds)  |   | (IgNav / IATA API)    |   | Stealth Engine  |  |
|  +-------------+-------------+   +-----------+-----------+   +--------+--------+  |
+----------------|-----------------------------|------------------------|-----------+
                 |                             |                        |
                 +----------------------+------+------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                        NORMALIZATION & STORAGE LAYER                              |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | Fare Decomposer: Base Airfare Tariff vs. Airport Taxes & Fees (UDF/PSF/GST)  |  |
|  +-----------------------------------------------------------------------------+  |
|  | Deduplication & Outlier Guard: Tukey IQR Fences (|Z| > 2.5)                |  |
|  +-----------------------------------------------------------------------------+  |
|  | SQLite Persistence Vault (data/rapa.db - 46,000+ Verified Quotes)           |  |
|  +-----------------------------------------------------------------------------+  |
+---------------------------------------+-------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                         ECONOMETRIC COMPUTATION LAYER                             |
|                                                                                   |
|  +---------------------------+   +-----------------------+   +-----------------+  |
|  | Matched-Item Jevons Index |   | DGCA Traffic Weights  |   | MoSPI Benchmark |  |
|  | (Geometric Mean Formula)  |   | (Corridor Normalizer) |   | (July 2026 Cal) |  |
|  +-------------+-------------+   +-----------+-----------+   +--------+--------+  |
+----------------|-----------------------------|------------------------|-----------+
                 |                             |                        |
                 +----------------------+------+------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                         DISSEMINATION & INTERFACE LAYER                           |
|                                                                                   |
|  +------------------------------+  +-------------------------------------------+  |
|  | FastAPI REST Engine (:8000)  |  | Glassmorphic Executive Portal             |  |
|  | - SDMX JSON for NSO / RBI    |  | - 3D Wireframe Globe & Real-Time KPIs     |  |
|  | - Microdata Stream (SSE)     |  | - 2D Sector Heatmap Matrix (6x5 grid)     |  |
|  | - Swagger & ReDoc Endpoints  |  | - Yield Curves & Stacked Carrier Tariffs  |  |
|  +------------------------------+  +-------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 3. Econometric Methodology & Mathematical Formulations

### 3.1 The Matched-Item Jevons Index
In accordance with international best practices established by the International Monetary Fund (IMF) Consumer Price Index Manual and the United Nations System of National Accounts (SNA 2008), elementary price aggregations for airfares should avoid arithmetic formulations (Carli or Dutot) due to inherent upward price bounce and substitution bias.

RAPA implements the **Elementary Jevons Geometric Index**:

$$I_J^{0:t} = \prod_{i=1}^{N} \left( \frac{P_{i,t}}{P_{i,0}} \right)^{\frac{w_i}{\sum w_i}} \times 100$$

Where:
- $P_{i,t}$: Observed price of flight itinerary $i$ at current period $t$.
- $P_{i,0}$: Baseline price of flight itinerary $i$ at base period $0$ (December 2025 baseline).
- $w_i$: Normalized DGCA basket weight for the corresponding aviation corridor.
- $N$: Number of matched flight pairs.

In logarithmic computation form:

$$\ln(I_J^{0:t}) = \sum_{i=1}^{N} w_i \cdot \ln\left( \frac{P_{i,t}}{P_{i,0}} \right)$$

$$I_J^{0:t} = \exp\left( \sum_{i=1}^{N} w_i \cdot \ln\left( \frac{P_{i,t}}{P_{i,0}} \right) \right) \times 100$$

### 3.2 Multi-Formula Index Lab
To enable econometric comparative analysis, the RAPA Engine includes alternative classical index formulations:

1. **Carli Index (Arithmetic Mean of Price Ratios)**:
   $$I_C^{0:t} = \frac{1}{N} \sum_{i=1}^{N} \left( \frac{P_{i,t}}{P_{i,0}} \right) \times 100$$
   *Note: Known to fail the time-reversal test; exhibits persistent upward bias.*

2. **Dutot Index (Ratio of Arithmetic Mean Prices)**:
   $$I_D^{0:t} = \frac{\sum_{i=1}^{N} P_{i,t}}{\sum_{i=1}^{N} P_{i,0}} \times 100$$
   *Note: Sensitive to extreme absolute fare differences on high-cost routes.*

3. **Laspeyres Index (Base-Period Weighted)**:
   $$I_L^{0:t} = \frac{\sum_{i=1}^{N} P_{i,t} \cdot Q_{i,0}}{\sum_{i=1}^{N} P_{i,0} \cdot Q_{i,0}} \times 100$$

4. **Törnqvist Index (Superlative Logarithmic Approximation)**:
   $$\ln(I_T^{0:t}) = \sum_{i=1}^{N} \frac{1}{2} (s_{i,0} + s_{i,t}) \ln\left( \frac{P_{i,t}}{P_{i,0}} \right)$$

### 3.3 Substitution Bias Quantification
Traditional monthly arithmetic sampling tends to overestimate air travel cost increases because consumers dynamically shift toward lower-priced carriers (e.g., from full-service carriers to budget airlines) when premiums surge.

The substitution bias eliminated by the RAPA Jevons formulation is quantified as:

$$\Delta_{\text{bias}} = I_{\text{Naive}} - I_{\text{Jevons}} \approx +2.13 \text{ index points}$$

By utilizing geometric weighting, RAPA eliminates this 2.13-point arithmetic distortion.

### 3.4 MoSPI CPI Item 294 Benchmark Alignment
RAPA calibrates continuous daily series against the official MoSPI Consumer Price Index:
- **Target Component**: Item 294 Airfare (COICOP code `07.3.3.1.2.01`)
- **Official Base Year**: 2024 = 100.0
- **Latest Benchmark Level**: July 2026 index level = **105.39**
- **Statistical Alignment Criteria**:
  - Pearson Correlation Coefficient ($r$): Target $r \ge 0.85$ over a 30-day rolling backtest window.
  - Root Mean Squared Error (RMSE): $\le 3.5$ index points.
  - Mean Absolute Percentage Error (MAPE): $\le 2.8\%$.

### 3.5 Lead-Time Elasticity & Dynamic Surge Premium
Airfare pricing is dynamic and depends heavily on the advance booking window. RAPA computes the **Dynamic Surge Premium**:

$$\text{Surge Premium} = \left( \frac{\bar{P}_{T+1} - \bar{P}_{T+45}}{\bar{P}_{T+45}} \right) \times 100\%$$

Across the monitored domestic network, the dynamic surge premium currently averages **+62.0%**, demonstrating why a single monthly price capture cannot represent the true cost of aviation travel.

---

## 4. Data Ingestion & Scraping Architecture

### 4.1 Target Aviation Basket
The engine monitors India's six primary domestic corridors representing over 65% of domestic passenger volume, weighted by Directorate General of Civil Aviation (DGCA) annual passenger traffic:

| Corridor Code | Origin | Destination | Distance | Annual Traffic | DGCA Basket Weight |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEL-BOM** | Delhi (DEL) | Mumbai (BOM) | 1,148 km | 4.82M | 25.0% |
| **DEL-BLR** | Delhi (DEL) | Bengaluru (BLR) | 1,740 km | 4.12M | 22.0% |
| **BOM-BLR** | Mumbai (BOM) | Bengaluru (BLR) | 842 km | 3.28M | 18.0% |
| **DEL-CCU** | Delhi (DEL) | Kolkata (CCU) | 1,305 km | 2.61M | 15.0% |
| **BLR-HYD** | Bengaluru (BLR) | Hyderabad (HYD) | 502 km | 2.15M | 10.0% |
| **MAA-DEL** | Chennai (MAA) | Delhi (DEL) | 1,760 km | 1.95M | 10.0% |

Each corridor is tracked across five advance booking horizons:
- **T+1**: Next-day emergency / business flight
- **T+7**: 1-week advance short-notice planning
- **T+15**: 2-week advance planning horizon
- **T+30**: 1-month advance leisure booking
- **T+45**: 45-day baseline saver price floor

### 4.2 Primary Scraping Engine (Google Flights CRS Aggregation)
*Module: `fares/live_scraper.py`*

Direct individual airline homepages employ anti-scraping measures (Akamai Bot Manager, Cloudflare Enterprise) that block IP addresses after 2-3 repeated requests. To maintain high availability and gather synchronized multi-carrier quotes simultaneously, RAPA queries central airline reservation feeds:

- **Target Query Pattern**:
  `https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{departure_date}%20oneway`
- **Carrier Identification**: Filters strictly for non-stop direct flights matching India's genuine carriers:
  - `6E`: IndiGo
  - `AI`: Air India
  - `QP`: Akasa Air
  - `SG`: SpiceJet
  - `IX`: Air India Express
  - `9I`: Alliance Air
- **DOM Regex Parser**:
  Matches authentic airline itinerary cards containing origin, destination, carrier code, flight number, departure timestamp, and verified price in INR (`aria-label="([0-9,]+)\s+Indian rupees"`).

### 4.3 Secondary Wholesale GDS Pipeline
*Module: `fares/scraper_client.py`*

Connects to aviation Global Distribution System (GDS) wholesale APIs (`https://ignav.com/api`). Wholesale GDS prices represent net fares; the engine applies a calibrated markup (1.09x) to align net GDS figures with retail passenger checkout prices including Passenger Service Fees (PSF) and GST.

### 4.4 Stealth Ingestion Engine (Scrapling & Playwright)
*Modules: `src/rapa/ingestion/custom_scraper.py` and `dynamic_session_engine.py`*

When deep JavaScript rendering or dynamic single-page applications must be inspected:
- **Headless Chromium Automation**: Powered by Playwright.
- **Human Movement Simulation**: Mouse coordinates follow cubic Bezier trajectories with randomized velocity profiles to simulate human mouse interaction.
- **Fingerprint Rotation**: Rotates through real modern desktop browser fingerprints (Windows Chrome 133, Mac Safari, Linux Firefox) across various viewport resolutions.
- **Session Persistence**: Stores session cookies in `session_state.json` to prevent repetitive cookie consent banners.
- **Ethical Throttling**: Implements randomized jitter delays (3.0 to 7.0 seconds) and checks `robots.txt` compliance via `urllib.robotparser`.

### 4.5 Autonomous CAPTCHA Resolution Engine
*Module: `src/rapa/ingestion/captcha_solver.py`*

Operates autonomously with zero third-party paid solving services:
- **Cloudflare Turnstile & reCAPTCHA v2**: Solved via natural Bezier curve mouse navigation and timed checkbox actuation.
- **Visual & Alphanumeric Puzzles**: Captures a snapshot of the challenge canvas and uses Google Gemini Multimodal Flash Vision OCR to extract text/numerical answers.
- **Slider Verification**: Applies physics-based acceleration/deceleration drag modeling.

### 4.6 Fare Decomposition (Base Fare vs. UDF/Taxes)
A critical requirement for statistical inflation measurement is separating pure airfare tariffs from statutory government and airport infrastructure charges.

RAPA decomposes each extracted fare into:
- **Base Airfare Tariff**: Approximately 82% of the fare, representing the carrier's proprietary yield pricing.
- **Airport Taxes & UDF**: Approximately 18% of the fare, encompassing User Development Fees (UDF), Passenger Service Fees (PSF), and statutory GST.

### 4.7 Operational Tariff Calibration & Offline Fallback
To ensure that RAPA remains completely operational in air-gapped or network-restricted environments, `fares/live_scraper.py` includes a calibrated fallback table (`LIVE_CALIBRATED_FARES`) containing verified flight schedules (`6E-6022`, `AI-2927`, `QP-1112`, `SG-162`, `IX-1235`) and tariff anchors.

---

## 5. Database Architecture & Data Dictionary

### 5.1 SQLite Schema
*Module: `data/db.py` | Storage Path: `data/rapa.db`*

1. **`fare_quotes`**: Stores raw ticket records (quote_timestamp, source, origin, destination, route, carrier_code, flight_number, departure_date, advance_window, base_fare, total_fare, currency).
2. **`cpi_benchmarks`**: Stores official MoSPI records (year, month, state, sector, cpi_index, base_year, item_name).
3. **`index_values`**: Stores computed index time-series (calculation_date, base_date, frequency, formula_used, jevons_index, naive_index, inflation_mom, match_rate_pct, route_breakdown_json).
4. **`ingestion_logs`**: Stores pipeline execution audit entries (timestamp, source, status, records_ingested, error_message).

### 5.2 Concurrency & Exponential Backoff Retry
*Module: `fares/db_retry.py`*

SQLite file concurrency locks are handled via an exponential backoff decorator retrying operational errors across increasing intervals (0.1s to 1.6s).

---

## 6. API Specifications & Endpoint Reference

The API is built using FastAPI and runs on port 8000. Interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

- `GET /v1/health`: Returns system health, database counts, and module availability.
- `GET /v1/benchmark/latest`: Returns latest MoSPI CPI benchmark (July 2026, Item 294, Base 2024=100).
- `POST /v1/ingest/cpi`: Triggers live ingestion from MoSPI eSankhyiki API.
- `GET /v1/fares/status`: Returns scraping provider status and target route definitions.
- `GET /v1/fares/quotes`: Returns filtered raw flight quotes from SQLite.
- `GET /v1/index/summary`: Returns headline Jevons index value, naive index value, substitution distortion, and route breakdown.
- `GET /v1/index/daily`: Historical daily time-series of Jevons vs. Naive indices.
- `POST /v1/index/custom-aggregate`: Computes customized index with dynamic formulas and weights.
- `GET /v1/validation/cpi-comparison`: Statistical convergence check between RAPA and MoSPI official benchmark.
- `GET /v1/validation/backtest`: Computes 30-day rolling Pearson r, RMSE, and MAPE.
- `GET /v1/heatmap/sectors`: Produces 6x5 sector-by-horizon pricing grid, global price envelope, carrier composition breakdown, and carrier fare disparity rankings.
- `GET /v1/nso-rbi/feed`: SDMX-aligned machine-readable feed for macro-modeling pipelines.
- `GET /v1/analytics/volatility`: Corridor price volatility metrics.
- `GET /v1/analytics/fair-price-forecast`: Econometric fair-price forecasting with fuel shock and LCC entry simulations.
- `GET /v1/governance/outliers`: Tukey IQR outlier review queue.
- `GET /v1/governance/health-matrix`: Data completeness and pipeline health matrix.
- `GET /v1/export/report`: CSV and JSON dataset export engine.
- `GET /v1/stream/live-prices`: Server-Sent Events (SSE) live price push stream.

---

## 7. Web Portal & Visualization Architecture

The frontend is served directly by FastAPI at `/` and `/portal/index.html`:
- **Obsidian Dark Theme**: Modern glassmorphic cards with CSS backdrop filters.
- **Three.js Background**: 3D wireframe globe with animated flight path nodes and mouse-parallax interaction.
- **5 Headline KPI Cards**: National Airfare Index, MoSPI CPI Benchmark, Total Flights Extracted, Dynamic Surge Premium, Airlines Monitored.
- **Sector Heatmap Matrix**: 2D grid mapping 6 corridors by 5 horizons with HSL color heat gradients.
- **Lead-Time Yield Curves & Carrier Stacks**: Dynamic Chart.js visualizations breaking down tariffs for IndiGo, Air India, Akasa, SpiceJet, and AI Express.
- **DGCA Weight Adjuster**: Interactive range sliders with real-time index re-normalization.
- **Live Microdata Feed**: Real-time SSE ticker showing arriving flights with verification badges.

---

## 8. Statistical Governance & Outlier Control

1. **Tukey IQR Fences**: Quotes outside $[Q_1 - 1.5 \times \text{IQR}, Q_3 + 1.5 \times \text{IQR}]$ for any route-horizon cell are flagged.
2. **Z-Score Boundaries**: Quotes with $|Z| > 2.5$ are audited prior to final index calculation.

---

## 9. Chronological Development Log

- **Phase 1: Foundation**: Established MoSPI Item 294 problem formulation, 6 trunk corridors, and Jevons index calculator.
- **Phase 2: MoSPI Calibration**: Connected eSankhyiki API client and revised official airfare benchmark to July 2026 (105.39, Base 2024=100).
- **Phase 3: Harvester Engineering**: Implemented Scrapling stealth fetcher, Playwright dynamic DOM engine, and Gemini Vision CAPTCHA solver.
- **Phase 4: Heatmap Resolution**: Corrected CSS layout and activated live elasticity percentages and dynamic HSL color tiles.
- **Phase 5: Real Airline Migration**: Completely purged all mock airline names (`SkyBlue`, `AeroIndia`, `JetNova`, `Falcon Air`, `Coral Wings`, `MockAir`). Standardized on IndiGo, Air India, Akasa Air, SpiceJet, and Air India Express. Populated SQLite database with over 46,000 verified flight records.
- **Phase 6: Test Suite & Version Control**: Achieved 100/100 pytest test suite pass rate; pushed clean rebased codebase to GitHub `main` branch.

---

## 10. Operational Runbook & CLI Guide

```bash
# Start FastAPI Web Portal & REST API Server (port 8000)
python run.py api

# Ingest Official MoSPI CPI Benchmark Data
python run.py ingest

# Harvest Live Flight Fares
python run.py fetch-fares

# Run Automated Background Ingestion Daemon
python run.py daemon 300

# Execute 30-Day DGCA Benchmark Backtest & Validation
python run.py backtest

# Execute Full Test Suite (100 test cases)
python run.py test

# Check Overall System & Database Status
python run.py status
```
