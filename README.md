# FinSense AI — S&P Global × CRISIL Phase III Risk Intelligence Platform
## Module A: AI/NLP Risk Engine & Tactical Stock Index Rebalancer

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_19_TypeScript-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Database](https://img.shields.io/badge/Database-PostgreSQL_|_SQLite_Fallback-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Market Data](https://img.shields.io/badge/Market_Data-yfinance-green)](https://github.com/ranaroussi/yfinance)
[![Tests](https://img.shields.io/badge/Tests-71_Passing-brightgreen)](#)
[![Zero Paid APIs](https://img.shields.io/badge/APIs-100%25_Free_&_Open_Source-brightgreen)](#)

---

## Submission Details — S&P Global & CRISIL Campus Hackathon 2026

**Candidate Name:** Karaka Tejaswanth  
**College Email ID:** karaka.tejaswanth2023@vitstudent.ac.in  
**College / Campus:** Vellore Institute of Technology (VIT), Vellore  
**Module:** Module A — AI/NLP Risk Engine & Tactical Stock Index Rebalancer  
**Demo Video (YouTube Unlisted):** https://www.youtube.com/watch?v=CCwh2Zyxdgw  
**Presentation Deck:** [docs/presentation.pdf](docs/presentation.pdf)  
**Source Repository:** https://github.com/Teja-k057/FinSense-AI

> The demo video is hosted as an unlisted YouTube video. Please test the link in a private/incognito window before submitting.

---

## 1. Project Overview / Problem Statement & Approach

FinSense AI explores how financial news can be converted into transparent stock-index allocation proposals. It ingests news headlines from GDELT and a public Financial News PhraseBank mirror, classifies event categories, scores sentiment and impact, and combines the resulting signals with market-momentum data.

The tactical rebalancer applies bounded allocation constraints across a 15-stock mock universe: each constituent has a 2% minimum and 15% maximum weight, with portfolio weights normalized to 100%. A dashboard exposes the news, risk signals, target weights, and stock-level explanations. A historical simulator compares the tactical strategy with an equal-weight baseline using an assumed 10 bps transaction-cost model. This is an academic prototype—not investment advice or an official S&P Global/CRISIL methodology.

## 2. Architecture & Tech Stack

![FinSense AI system architecture](docs/architecture.png)

**Flow:** Public financial news / market data → ingestion and deduplication → sentiment, event, and impact analysis → signal fusion → constrained allocation → explanatory dashboard and historical comparison.

**Technology:** Python, FastAPI, SQLAlchemy, SQLite by default (PostgreSQL configuration supported), React, TypeScript, Vite, yfinance, and Python data-science libraries. The default sentiment engine is an explainable financial lexicon. Optional local FinBERT inference can be enabled with the relevant Transformers/PyTorch dependencies and configuration.

## 3. Dataset Used

- **GDELT 2.0 DOC API:** public news results retrieved at run time; availability and historical coverage depend on the upstream service.
- **Financial News PhraseBank:** a public financial-news sentiment corpus accessed through the URL configured in the application.
- **Local demonstration sample:** the application can generate a small CSV of example headlines for ingestion when no local sample file exists. These are demonstration examples and should not be represented as live news.
- **Market data:** price history and quotes requested through yfinance, subject to upstream availability and caching.

No confidential S&P Global or CRISIL client data is used. The index is a 15-stock mock universe. News labels, impact scores, market data availability, and historical backtest results depend on the configured data and run time.

## 4. Quickstart & Installation

**Runtime:** Python 3.10+ and Node.js 18+ with npm. Tested run commands are documented below; run them from the repository root.

```bash
git clone https://github.com/Teja-k057/FinSense-AI.git
cd FinSense-AI
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

On Windows, start both services using:

```powershell
.\scripts\run_dev.bat
```

Alternatively, start the backend and frontend in separate terminals:

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
cd frontend
npm run dev
```

Dashboard: http://localhost:5173  
Backend API docs: http://localhost:8000/docs

For optional database configuration, copy `.env.example` to `.env` and review the settings. Do not commit secrets or a populated local database.

## 5. Key Results & Domain Impact

The prototype demonstrates the full path from unstructured news to bounded portfolio-weight proposals, including sentiment, event labels, impact scores, reasons for weight changes, and historical comparison against an equal-weight mock index. The allocation rules target a 2% floor, 15% cap, and 100% total portfolio weight; the backtest uses a stated 10 bps transaction-cost assumption.

Performance metrics are run-dependent and should be quoted together with the selected date range and rebalancing frequency shown in the dashboard. Results are simulated, may change when market data or signals change, and do not demonstrate realized investment performance.

---

## 📌 Executive Summary

**FinSense AI** is an institutional-grade financial intelligence and index rebalancing platform built for the **S&P Global × CRISIL Phase III Case Study Competition**.

The platform implements **MODULE A: Tactical High-Frequency Stock Index Rebalancer**:
1. **Unstructured Data Ingestion**: Automatically acquires real-time business and market news from the **GDELT 2.0 API** and verified financial corpora from the **Kaggle Financial News PhraseBank** into a canonical schema.
2. **Unified AI/NLP Risk Engine**: Evaluates news text to produce:
   - **Directional Sentiment Score**: Continuous scale in $[-1.0, +1.0]$.
   - **Event Classification**: 10-class controlled taxonomy (*Geopolitical, Macroeconomic, Credit Event, Merger/Acquisition, Product Launch, Regulatory, Earnings, Supply Chain, Cybersecurity, Other*).
   - **Impact Score**: Explainable 5-factor calibrated impact rating in $[1.0, 10.0]$.
   - **Risk Level**: `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`.
3. **Tactical Stock Index Rebalancer**: Dynamically transforms NLP risk signals and live `yfinance` market movements into target weights for a **15-Stock Mock Index Universe** under strict institutional constraints:
   $$\sum_{i=1}^{15} w_i = 100.0\%, \quad 2.0\% \le w_i \le 15.0\%$$
4. **Historical Backtesting Engine**: Evaluates the **Baseline (Equal-Weight) Index** versus the **NLP Tactical Strategy** with strict **anti-look-ahead bias** and realistic **10 bps ($0.10\%$) transaction fee** deduction.
5. **Interactive FinSense AI Dashboard**: A modern, dark-mode terminal user interface providing real-time visibility into allocations, risk feeds, signal attribution, and historical performance.

---

## 🚀 Quickstart Guide (How to Run)

### 📋 Prerequisites
- **Python**: Version `3.10` or higher (`3.11`, `3.12`, `3.13`, or `3.14`)
- **Node.js**: Version `18.0` or higher & `npm`
- **Git**

---

### Option A: 1-Click Launch (Recommended for Windows)

From the project root directory, run either launcher script:

- **Command Prompt / File Explorer**: Double-click or run `scripts\run_dev.bat` (or `run.bat` in the workspace root).
- **PowerShell**:
  ```powershell
  .\scripts\run_dev.ps1
  ```

This automatically opens two dedicated windows:
1. **FastAPI Backend Server** running on `http://localhost:8000`
2. **React + Vite Frontend Dev Server** running on `http://localhost:5173`

---

### Option B: Step-by-Step Manual Launch

#### Step 1: Open the Project Directory
Ensure your terminal is in the project folder:
```bash
cd FinSense-AI
```

#### Step 2: Install Dependencies (If not already installed)
```bash
# Python backend packages
pip install -r requirements.txt

# Frontend packages
cd frontend
npm install
cd ..
```

#### Step 3: Configure Environment Variables
Ensure a local `.env` file exists (a default `.env` is already configured for SQLite):
```bash
# On Linux / macOS:
cp .env.example .env

# On Windows PowerShell:
Copy-Item .env.example .env
```
*The system runs out-of-the-box with **SQLite** (`data/risk_engine.db`). If PostgreSQL is desired, update `DATABASE_URL` in `.env`.*

#### Step 4: Initialize the Database
Ensure database schemas and mock universe companies are initialized:
```bash
python -m backend.app.database.migrations
```
*Verifies all 8 database tables (`news_documents`, `risk_signals`, `companies`, `index_constituents`, `market_data_records`, `rebalance_runs`, `rebalance_decisions`, `data_source_logs`) and creates required performance indexes.*

#### Step 5: Start the Backend API (FastAPI)
In Terminal 1:
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

#### Step 6: Start the Frontend UI (React + Vite)
In Terminal 2:
```bash
cd frontend
npm run dev
```
- **FinSense AI Dashboard**: **[http://localhost:5173](http://localhost:5173)**

---

## 🧪 Running Automated Tests

Run the full test suite across all modules (Ingestion, NLP, Market Data, Rebalancing, Backtesting, Database Storage, API):
```bash
python -m unittest discover -s tests -p "test_*.py"
```
*Current test status: **71 tests passing (100% OK)**.*

To test individual modules:
```bash
# Test Database Storage & Models
python -m unittest discover -s tests -p "test_database_storage.py"

# Test Tactical Rebalancing Engine
python -m unittest discover -s tests -p "test_rebalancing_engine.py"

# Test Historical Backtesting Framework
python -m unittest discover -s tests -p "test_backtesting.py"

# Test FastAPI Endpoints
python -m unittest discover -s tests -p "test_fastapi_risk_api.py"
```

To validate the frontend build:
```bash
cd frontend
npm run build
```

---

## 📊 Dashboard Overview

The React dashboard is organized into 7 primary sections matching the competition specifications:

| Section | Description |
| :--- | :--- |
| **1. Executive Overview** | 5 Top KPI Cards: Tracked Stocks (15), News Articles (Today), High-Impact Events ($\ge 7$), Negative Signals, and Positive Signals. |
| **2. Rebalancing Allocation** | Interactive Dual-Bar Chart comparing **Before (Baseline 6.67%)** vs **After (Target Weight %)** with hover callouts showing the event rationale. |
| **3. Current Index Allocation** | Donut chart displaying constituent weights totaling **100% Total Weight** with color-coded legend. |
| **4. Live News Feed** | Chronological feed of ingested news headlines with relative timestamps, sentiment tags (`Positive`, `Negative`), and ticker badges. |
| **5. Latest Risk Signals** | Tabular feed of NLP signals: Company, continuous sentiment, 10-class event taxonomy, impact rating, and tactical recommendation. |
| **6. Stock Weight Changes** | Decision table showing Before %, After %, net change $\Delta w$, and tactical action (`Increase`, `Hold`, `Reduce`). |
| **7. Backtest & Event Distribution** | Dual equity curves (**AI Rebalanced Index** vs **Equal Weighted Index**) net of 10 bps fees, alongside a 10-class event distribution donut. |

---

## 🏛 System Architecture & Project Structure

```
FinSense-AI/
├── backend/
│   ├── alembic/                       # Alembic database migrations
│   │   ├── versions/                  # Schema migration files
│   │   └── env.py
│   ├── app/
│   │   ├── api/                       # FastAPI REST routes
│   │   │   ├── routes_health.py       # Health check & DB status
│   │   │   ├── routes_ingest.py       # Live GDELT & Kaggle ingestion triggers
│   │   │   ├── routes_risk.py         # Risk signals & news query endpoints
│   │   │   ├── routes_rebalancer.py   # Module A rebalance & backtest endpoints
│   │   │   └── __init__.py            # API router mount
│   │   ├── config/                    # Pydantic v2 application settings (.env)
│   │   ├── database/                  # SQLAlchemy ORM models & connection
│   │   │   ├── models.py              # 8 Core DB Tables (News, Signal, Constituent, etc.)
│   │   │   ├── connection.py          # Dual PostgreSQL / SQLite engine
│   │   │   └── migrations.py          # Auto-migrator & 15-stock universe seeder
│   │   ├── ingestion/                 # Data Acquisition Layer
│   │   │   ├── gdelt.py               # Real-time GDELT 2.0 DOC API client
│   │   │   ├── kaggle.py              # Financial PhraseBank mirror acquisition
│   │   │   └── pipeline.py            # Canonical ingestion & deduplication
│   │   ├── nlp/                       # AI/NLP Risk Engine
│   │   │   ├── sentiment.py           # Directional FinBERT sentiment [-1, +1]
│   │   │   ├── event_classifier.py    # 10-Class financial taxonomy classifier
│   │   │   └── impact_scorer.py       # 5-factor calibrated impact scoring [1, 10]
│   │   ├── portfolio/                 # Market Data Layer
│   │   │   ├── market_data.py         # Live yfinance quotes, returns, & volatility
│   │   │   └── models.py              # Portfolio holding & constituent models
│   │   ├── rebalancer/                # Module A Tactical Rebalancing Engine
│   │   │   ├── rebalancing_engine.py  # Water-filling allocation algorithm (2%-15%)
│   │   │   ├── models.py              # Rebalance request & response schemas
│   │   │   ├── backtester.py          # Anti-look-ahead historical backtester
│   │   │   └── backtest_models.py     # Backtesting performance schemas
│   │   └── main.py                    # Application entry point & CORS
│   └── alembic.ini                    # Alembic config
├── frontend/                          # React 19 + TypeScript + Vite Dashboard
│   ├── src/
│   │   ├── components/                # Modular UI components
│   │   │   ├── FinSenseDashboard.tsx  # Main dashboard layout matching reference UI
│   │   │   ├── LiveRiskFeed.tsx       # Filterable news & risk signals feed
│   │   │   ├── IndexCompositionTable.tsx # 15-Stock constituent sortable table
│   │   │   ├── SignalExplanationCard.tsx # Transparent WHY attribution card
│   │   │   ├── StockDetailSection.tsx # Selected company deep-dive
│   │   │   ├── BacktestView.tsx       # Historical backtest equity curve & metrics
│   │   │   └── AdHocAnalyzerModal.tsx # Interactive headline risk analyzer modal
│   │   ├── services/api.ts            # Typed HTTP API client
│   │   ├── types/index.ts             # TypeScript interfaces matching backend models
│   │   ├── App.tsx                    # React application coordinator
│   │   └── index.css                  # FinSense AI dark terminal design system
│   ├── package.json
│   └── vite.config.ts
├── tests/                             # Automated test suite (71 tests)
├── data/                              # Local SQLite database & cache directory
├── requirements.txt                   # Python package dependencies
├── .env.example                       # Environment configuration template
└── README.md                          # Platform documentation
```

---

## 📡 REST API Reference

### Health & System
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service status, environment, and database connection. |

### Module A: Tactical Rebalancer & Backtest
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/rebalancer/index` | Retrieves the 15-stock mock index universe with baseline weights. |
| `GET` | `/api/v1/rebalancer/latest` | Retrieves the most recent tactical rebalancing summary from cache/DB. |
| `POST` | `/api/v1/rebalancer/rebalance` | Executes water-filling tactical rebalancing across all constituents. |
| `POST` | `/api/v1/rebalancer/backtest` | Runs historical backtest simulation (Baseline vs NLP Strategy). |

### NLP Risk Engine & News Feeds
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/risk-signals` | Paginated risk signals with company, impact, and date filters. |
| `GET` | `/api/v1/risk-signals/{company}` | Historical risk signals for a specific stock ticker. |
| `POST` | `/api/v1/analyze` | Real-time ad-hoc headline analysis (sentiment, event, impact, action). |
| `GET` | `/api/v1/news` | Filterable canonical news documents from GDELT & Kaggle. |
| `GET` | `/api/v1/companies` | 15-stock universe with live quotes, sector, and risk levels. |
| `GET` | `/api/v1/events` | List of supported 10-class financial taxonomy events. |

### Data Ingestion Triggers
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/ingest/gdelt` | Triggers live polling of the GDELT Project v2 API. |
| `POST` | `/api/v1/ingest/kaggle` | Loads and normalizes Kaggle Financial News PhraseBank articles. |

---

## ⚖️ Institutional Constraints & Mathematical Methodology

### 1. Tactical Allocation Formula
For each constituent $i$ in the index:
$$\text{Signal}_i = 0.50 \cdot s_i + 0.30 \cdot \left(\frac{I_i - 5.0}{5.0}\right) + 0.20 \cdot \tanh(10 \cdot r_i)$$
Where:
- $s_i \in [-1.0, +1.0]$: Aggregated recent FinBERT sentiment score.
- $I_i \in [1.0, 10.0]$: Calibrated event impact score.
- $r_i$: Recent price momentum return from `yfinance`.

### 2. Water-Filling Constrained Optimization
Target weights $w_i^*$ are computed by adjusting baseline weights $w_{0,i} = 6.67\%$ by tactical tilt $\Delta w_i = \text{Signal}_i \cdot 0.035$, subject to:
1. **Floor**: $w_i^* \ge 2.0\%$ (prevents constituent elimination).
2. **Cap**: $w_i^* \le 15.0\%$ (prevents over-concentration in single names).
3. **Budget Invariant**: $\sum_{i=1}^{15} w_i^* = 100.0\%$ (exact water-filling reallocation).

### 3. Anti-Look-Ahead Bias Backtesting
At each simulated historical rebalancing date $t_k$:
- Only news signals published strictly at or before $t_k$ are visible.
- Target weights $w_k^*$ are determined at $t_k$.
- Subsequent index returns are evaluated over $(t_k, t_{k+1}]$.
- Transaction costs of **10 bps ($0.10\%$)** are deducted for all two-way portfolio turnover.

---

## 🔒 Security & Best Practices
- **Zero API Credentials Stored in DB**: All external API tokens and environment secrets reside strictly in `.env`.
- **Relational Integrity**: Foreign keys, unique constraints, and B-tree indexes on `company`, `timestamp`, `source`, and `event_type`.
- **Zero Hallucinated Market Prices**: Market quotes and returns are pulled directly from `yfinance` with explicit error handling for missing tickers.
