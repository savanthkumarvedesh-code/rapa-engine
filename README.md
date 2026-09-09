# RAPA: Real-Time Airfare Price Augmentation

A high-frequency airfare inflation measurement and official CPI augmentation engine built for India's **National Statistical Office (NSO / MoSPI)** and **Reserve Bank of India (RBI)**.

---

## 🏛️ Methodological & Data Architecture

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │   Official Macroeconomic Benchmark (NSO / MoSPI)       │
                                  │   Item 294: Airfare (Classification: 07.3.3.1.2.01)   │
                                  │   Division 7 (Transport) — Base 2024=100               │
                                  └──────────────────────────┬─────────────────────────────┘
                                                             │
                                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             RAPA Econometric Price Engine                                │
│                                                                                          │
│  ┌─────────────────────────────────┐           ┌──────────────────────────────────────┐  │
│  │   Route-Level Target Basket     │           │   Econometric Index Formulation      │  │
│  │   • DEL-BOM (25%)  • DEL-BLR (22%)│         │   • Primary: Matched-Item Jevons     │  │
│  │   • BOM-BLR (18%)  • DEL-CCU (15%)│         │   • Baseline: Naive Arithmetic       │  │
│  │   • BLR-HYD (10%)  • MAA-DEL (10%)│         │   • Axiom: Time-Reversal Validated   │  │
│  │   • Windows: T+1,7,15,30,45     │           │   • Real-Time Tracking Calibration   │  │
│  └─────────────────────────────────┘           └──────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Official CPI Benchmark vs. Regulatory Data
- **Official Benchmark**: Ingested via official `mospi-esankhyiki` package from MoSPI's eSankhyiki API. Verified down to **Item 294: "Airfare" (`code: 07.3.3.1.2.01`)** with state and urban/rural breakdown.
- **Methodological Caveat**: MoSPI CPI Item 294 represents the official macroeconomic inflation benchmark (Base 2024=100). This is distinct from DGCA regulatory airline tariff reports.

### 2. Route Separation
- `/v1/benchmark/*` — Official MoSPI CPI aggregate benchmarks.
- `/v1/fares/*` — Route-level real-time fare microdata and GDS collector status.
- `/v1/index/*` — High-frequency computed RAPA price indices (Jevons vs. Naive).
- `/v1/validation/*` — Calibration, tracking error, and divergence analysis.
- `/v1/health` & `/v1/logs` — Real-time telemetry and queryable ingestion audit trail.

---

## 🚀 Quickstart

### 1. Ingest Official MoSPI CPI Data
```bash
python run.py ingest
```

### 2. Run Test Suite (16 Unit & Integration Tests)
```bash
python run.py test
```

### 3. Launch FastAPI REST Service
```bash
python run.py api
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Validation Comparison: [http://localhost:8000/v1/validation/cpi-comparison](http://localhost:8000/v1/validation/cpi-comparison)

### 4. Check Status & Telemetry
```bash
python run.py status
```
