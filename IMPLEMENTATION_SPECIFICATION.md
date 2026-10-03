# S&P Global × CRISIL Phase III Case Study Competition
## Strategic AI/NLP Risk Engine + Downstream Portfolio Stress Testing (Module B)
### Complete Technical Architecture, Data Flows, and Implementation Blueprint

---

## Executive Summary

This specification outlines the end-to-end design and implementation of an institutional-grade **Financial Risk Intelligence Platform** built specifically for the **S&P Global × CRISIL Phase III Case Study Competition**.

The platform is divided into two tightly integrated systems:
1. **Core NLP Risk Engine**: Ingests unstructured financial news from **GDELT** and the **Kaggle Financial News dataset**, performs named entity recognition and ticker resolution, computes directional sentiment normalized to $[-1.0, +1.0]$ via FinBERT, classifies events across an 8-class financial taxonomy, and derives a calibrated Impact Score on a $[1, 10]$ scale to produce standardized, structured risk signals.
2. **Downstream Module B — Strategic Portfolio Stress Testing**: Integrates free market data via `yfinance`, maps unstructured risk signals to parametric asset return shocks and cross-asset contagion, and simulates portfolio resilience through Historical Crisis Replay, Dynamic NLP Shocks, and What-If Factor stress testing with Parametric/Historical Value at Risk (VaR 95% & 99%) and Expected Shortfall (CVaR).

The entire system requires **zero paid APIs** and operates fully deterministically with offline caching and graceful fallbacks.

---

## 1. Complete System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PRESENTATION TIER                                    │
│   Institutional React + TypeScript Dashboard (Vite, Tailwind CSS, Lucide, Recharts)     │
│  ┌─────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────────────┐ │
│  │   Live News & Signals   │ │ Portfolio Stress Console │ │ Financial Shock Analytics│ │
│  │   - Sentiment Gauge     │ │ - Holdings / Weights     │ │ - Parametric & Hist VaR  │ │
│  │   - Impact Matrix (1-10)│ │ - Scenario Selector      │ │ - Expected Shortfall     │ │
│  │   - Entity Graph Link   │ │ - Factor Beta Sliders    │ │ - Contagion & P&L Impact │ │
│  └─────────────────────────┘ └──────────────────────────┘ └──────────────────────────┘ │
└───────────────────────────────────────────▲────────────────────────────────────────────┘
                                            │ HTTP / REST & SSE (Server-Sent Events)
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                             API & ORCHESTRATION GATEWAY                                │
│                     FastAPI (Asynchronous, OpenAPI/Swagger 3.1)                         │
│  ┌──────────────────────────┐  ┌──────────────────────────┐ ┌────────────────────────┐ │
│  │   /api/v1/ingest         │  │   /api/v1/signals        │ │   /api/v1/stress-test  │ │
│  │   - Trigger GDELT fetch  │  │   - Filter by ticker     │ │   - Run Monte Carlo    │ │
│  │   - Upload Kaggle batch  │  │   - Score thresholding   │ │   - Parametric shock   │ │
│  │   - Trigger pipeline     │  │   - Export JSON / Parquet│ │   - Historical replay  │ │
│  └──────────────────────────┘  └──────────────────────────┘ └────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────────┬──────────────────┘
                           │                                          │
┌──────────────────────────▼──────────────────────┐ ┌─────────────────▼──────────────────┐
│              CORE NLP RISK ENGINE               │ │    MODULE B: PORTFOLIO STRESS ENGINE   │
│ ┌─────────────────────────────────────────────┐ │ │ ┌────────────────────────────────┐ │
│ │ 1. Ingestion Normalizer                     │ │ │ │ 1. Market Data Ingestion       │ │
│ │    (GDELT DOC 2.0 API + Kaggle CSV)         │ │ │ │    (yfinance: Prices, Returns) │ │
│ ├─────────────────────────────────────────────┤ │ │ ├────────────────────────────────┤ │
│ │ 2. Text Preprocessing                       │ │ │ │ 2. Statistical Calibration     │ │
│ │    (Regex, Lemmatization, Stopwords, HTML)  │ │ │ │    - Variance-Covariance Matrix│ │
│ ├─────────────────────────────────────────────┤ │ │ │    - Asset Betas & Volatilities│ │
│ │ 3. Entity Resolution Engine                 │ │ │ ├────────────────────────────────┤ │
│ │    (spaCy NER + S&P 500 Ticker/Alias Map)   │ │ │ │ 3. NLP-to-Shock Mapping Kernel │ │
│ ├─────────────────────────────────────────────┤ │ │ │    - Event Severity Transmiss. │ │
│ │ 4. Sentiment Classifier                     │ │ │ │    - Cross-Asset Contagion     │ │
│ │    (ProsusAI/FinBERT: Score [-1.0, +1.0])   │ │ │ ├────────────────────────────────┤ │
│ ├─────────────────────────────────────────────┤ │ │ │ 4. Stress Simulation Engine    │ │
│ │ 5. Financial Event Classifier               │ │ │ │    - Historical Scenario Replay│ │
│ │    (Zero-Shot / DistilRoBERTa 8-Class)      │ │ │ │    - Real-Time News Shock      │ │
│ ├─────────────────────────────────────────────┤ │ │ │    - VaR (95%/99%) & CVaR (ES) │ │
│ │ 6. Composite Impact Scorer                  │ │ │ └────────────────────────────────┘ │
│ │    (Score 1-10: Severity × Recency × Alpha) │ │ └────────────────────────────────────┘
│ └─────────────────────────────────────────────┘                                        │
└──────────────────────────┬─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────────────────────────┐
│                                 DATA PERSISTENCE TIER                                  │
│   - SQLite / DuckDB (ACID Relational Storage for Articles, Signals, Portfolios, Runs)   │
│   - Parquet / Arrow Cache (High-speed columnar storage for historical market returns)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Complete End-to-End Data Flow

```
                      [SOURCE 1: GDELT 2.0 API]        [SOURCE 2: Kaggle Financial News]
                                 │                                    │
                                 ▼                                    ▼
                      ┌─────────────────────────────────────────────────────────┐
                      │                   INGESTION PIPELINE                    │
                      │  - Deduplication (SHA-256 hash of headline + timestamp) │
                      │  - Timestamp normalization to UTC ISO-8601              │
                      │  - Payload format homogenization                        │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
                                                   ▼
                      ┌─────────────────────────────────────────────────────────┐
                      │                   TEXT PREPROCESSING                    │
                      │  - Strip boilerplate, markup, URL fragments             │
                      │  - Clean punctuation, expand financial contractions     │
                      │  - Retain currency symbols ($/€/£), percentages, bps    │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
                                                   ▼
                      ┌─────────────────────────────────────────────────────────┐
                      │              ENTITY EXTRACTION & RESOLUTION             │
                      │  - spaCy NER (ORG, PERSON, GPE)                         │
                      │  - Alias/Ticker Dictionary Resolution                   │
                      │    (e.g., "Alphabet" / "Google" -> "GOOGL")             │
                      │  - Secondary Sector Mapping (GICS Sectors)              │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
                        ┌──────────────────────────┴──────────────────────────┐
                        ▼                                                     ▼
         ┌──────────────────────────────┐                      ┌──────────────────────────────┐
         │     FINBERT SENTIMENT        │                      │   EVENT TAXONOMY CLASSIFIER  │
         │ - Output: [Pos, Neg, Neu]    │                      │ - Multi-class financial event│
         │ - Scaled Sentiment:          │                      │ - Output: Category + P(class)│
         │   S = P(pos) - P(neg) ∈ [-1,1│                      │   e.g., Credit / Regulatory  │
         └──────────────┬───────────────┘                      └──────────────┬───────────────┘
                        │                                                     │
                        └──────────────────────────┬──────────────────────────┘
                                                   │
                                                   ▼
                      ┌─────────────────────────────────────────────────────────┐
                      │                 COMPOSITE IMPACT SCORER                 │
                      │  Calculates Impact Score (1 to 10):                     │
                      │  Impact = f(|Sentiment|, Event_Weight, Source_Conf)     │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
                                                   ▼
                      ┌─────────────────────────────────────────────────────────┐
                      │            STRUCTURED RISK SIGNAL GENERATION            │
                      │  Published to DB & REST API:                            │
                      │  {event_id, ticker, sentiment, event_type, impact, ...} │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
                                                   ▼
                      ┌─────────────────────────────────────────────────────────┐
                      │                MODULE B: STRESS TESTING                 │
                      │  1. Ingest Portfolio (Tickers, Weights, Capital)        │
                      │  2. Fetch Market Data via yfinance (252-day history)    │
                      │  3. Calculate Asset Volatility & Covariance Matrix (Σ)  │
                      │  4. Translate Risk Signals into Asset Shock Vector (Δr) │
                      │  5. Compute Post-Shock Portfolio P&L, 95/99% VaR, CVaR  │
                      │  6. Simulate Sector Contagion Matrix Propagation        │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
                                                   ▼
                      ┌─────────────────────────────────────────────────────────┐
                      │                 DASHBOARD VISUALIZATION                 │
                      │  - Early warning risk alerts                            │
                      │  - Pre- vs. Post-shock distribution & VaR comparison    │
                      │  - Interactive portfolio rebalancing simulator          │
                      └─────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Layer | Component | Choice | Rationale |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Language | Python 3.11+ | Ecosystem compatibility with PyTorch, Transformers, spaCy, and NumPy/SciPy |
| **Backend Framework** | Web Server | FastAPI + Uvicorn | Async performance, strict Pydantic v2 schemas, auto-generated OpenAPI documentation |
| **NLP Transformer** | Sentiment | `ProsusAI/finbert` | Pretrained domain-specific BERT model for financial text with calibrated negative/positive logits |
| **Entity Recognition** | Extraction | `spaCy` (`en_core_web_sm`) + Regex | High-throughput token-level NER with custom financial alias/ticker gazetteer |
| **Event Classifier** | Taxonomy | Zero-Shot DistilBART / Keyword Engine | Robust categorization across 8 core financial risk categories without expensive manual fine-tuning |
| **Market Data** | Time Series | `yfinance` | Zero-cost programmatic access to historical prices, adjusted closes, and market beta calculations |
| **Risk Analytics** | Mathematical Engine | `numpy`, `pandas`, `scipy` | Fast matrix algebra, covariance calculations, parametric VaR, and historical tail distributions |
| **Database** | Storage Engine | SQLite with WAL mode + SQLAlchemy | Zero-configuration, file-based relational store; zero external database server required |
| **Frontend Framework** | UI Engine | React 18 + TypeScript + Vite | Type safety, component modularity, instant hot module reloading |
| **Styling & Icons** | Design System | Tailwind CSS + Lucide React | Institutional dark mode command center visual aesthetic (Bloomberg/CRISIL terminal style) |
| **Charts** | Data Visualization | Recharts | Composable SVG/Canvas financial charts (Waterfall P&L, VaR distribution curves, sector breakdown) |

---

## 4. ML/NLP Methodology

### 4.1. Text Preprocessing
Raw news items are sanitized through a deterministic pipeline:
1. **HTML & Boilerplate Removal**: Strip residual markup, tracking parameters, and publisher boilerplate (e.g., "Click here to subscribe", "Read full story on Bloomberg").
2. **Financial Symbol Preservation**: Protect key indicators such as currency signs (`$`, `€`, `£`, `₹`), percentage points (`%`), and basis points (`bps`).
3. **Contraction Expansion & Normalization**: Standardize terms such as `"Q1'24"` $\rightarrow$ `"Q1 2024"`, `"FY23"` $\rightarrow$ `"Fiscal Year 2023"`.

### 4.2. Named Entity Recognition & Ticker Resolution
1. **Token Extraction**: Run spaCy to detect `ORG` (Organizations) and `PERSON` (Key Executives).
2. **S&P 500 Ticker/Alias Mapping**:
   - Matches resolved strings against a structured company dictionary containing names, aliases, subsidiaries, and corresponding stock tickers (e.g., `"Google"` / `"Alphabet"` $\rightarrow$ `GOOGL`, `"Silicon Valley Bank"` $\rightarrow$ `SIVBQ`, `"JPMorgan Chase"` $\rightarrow$ `JPM`).
   - Fuzzy matching fallback (Levenshtein ratio $\ge 85\%$) for misspelled corporate entities.
   - Macro entities (e.g., `"Federal Reserve"`, `"OPEC"`, `"Semiconductors"`) are mapped to their representative sector ETF proxies (`XLF`, `XLE`, `SMH`).

### 4.3. Sentiment Scoring (Normalized to $[-1.0, +1.0]$)
- Model: `ProsusAI/finbert`.
- The model outputs softmax probability distribution across three classes:
  $$P(\text{positive}) + P(\text{negative}) + P(\text{neutral}) = 1.0$$
- Directional Sentiment Formulation:
  $$\text{Sentiment Score} = P(\text{positive}) - P(\text{negative})$$
- Range: $[-1.0, +1.0]$.
  - Severe credit distress or bankruptcy warning: $\approx -0.90$ to $-0.98$
  - Routine neutral regulatory filing: $\approx -0.05$ to $+0.05$
  - Major earnings beat and dividend hike: $\approx +0.80$ to $+0.95$

### 4.4. Financial Event Taxonomy (8 Classes)
Every news item is mapped into an 8-class risk taxonomy:
1. **Credit & Liquidity Distress** (e.g., default, downgrade, credit facility breach, liquidity crunch)
2. **Regulatory & Legal Penalties** (e.g., SEC investigation, antitrust lawsuits, compliance fines)
3. **Earnings & Financial Performance** (e.g., revenue miss, margin compression, guidance cuts)
4. **M&A and Corporate Restructuring** (e.g., hostile takeover, divestitures, balance sheet reorg)
5. **Supply Chain & Operational Disruption** (e.g., factory shutdown, component shortage, outage)
6. **Executive & Governance Turnover** (e.g., CEO resignation, whistleblower, board revolt)
7. **Macroeconomic & Monetary Policy** (e.g., interest rate shifts, CPI surprises, tariff changes)
8. **ESG & Reputational Risk** (e.g., environmental contamination, corporate governance scandal)

### 4.5. Impact Scoring Mathematical Formulation ($[1, 10]$ Scale)
The Impact Score reflects the potential market and solvency disruption caused by the event:

$$\text{Raw Impact} = \left( w_{\text{sent}} \cdot |\text{Sentiment}| + w_{\text{event}} \cdot W_{\text{event}} + w_{\text{conf}} \cdot C_{\text{source}} \right) \times V_{\text{entity}}$$

Where:
- $|\text{Sentiment}| \in [0.0, 1.0]$: Magnitude of sentiment polarity.
- $W_{\text{event}} \in [0.5, 1.0]$: Severity weight of event category (Credit = 1.0, Regulatory = 0.85, Earnings = 0.75, Governance = 0.60).
- $C_{\text{source}} \in [0.7, 1.0]$: Source confidence coefficient (GDELT verified outlet = 0.95; Kaggle verified feed = 0.90).
- $V_{\text{entity}} \in [1.0, 1.25]$: Systemic importance multiplier (Mega-cap systemic financial = 1.25, Mid-cap = 1.0).
- Weights: $w_{\text{sent}} = 0.50, w_{\text{event}} = 0.35, w_{\text{conf}} = 0.15$.

**Clamping & Scaling**:
$$\text{Impact Score} = \min\left(10, \max\left(1, \text{round}\left(\text{Raw Impact} \times 10\right)\right)\right)$$

---

## 5. GDELT Integration Approach (Source 1)

- **API Protocol**: GDELT 2.0 DOC API (`https://api.gdeltproject.org/api/v2/doc/doc?format=json`).
- **Targeted Query Strings**:
  - `query=(stocks OR earnings OR credit OR bankruptcy OR debt OR SEC) sourcelang:english&mode=artlist&maxrecords=50&sort=datedesc`
- **Fault-Tolerant Architecture**:
  1. Requests feature strict 5-second timeouts and automatic exponential backoff retry.
  2. Local caching: Successful queries are written to `backend/data/gdelt_cache/` to minimize redundant network bandwidth.
  3. Bundled Offline Snapshot: A pre-cached historical snapshot (featuring major market events such as the SVB collapse and First Republic liquidity crunch) guarantees 100% offline functionality.

---

## 6. Kaggle Dataset Integration Approach (Source 2)

- **Dataset Selection**: Daily Financial News for Stocks / Financial PhraseBank dataset.
- **Pre-Packaged Sample**: A seed file `backend/data/kaggle/financial_news_sample.csv` containing multi-sector financial headlines with verified dates and tickers.
- **Dynamic Ingestion Endpoint**: `POST /api/v1/ingest/kaggle` allows uploading arbitrary Kaggle financial news CSV files at runtime.
- **Automated Column Harmonization**: Dynamically detects column headers (`headline`/`title`, `stock`/`ticker`/`symbol`, `date`/`timestamp`).

---

## 7. yfinance Integration Approach

- **Data Harvested**:
  - Daily adjusted closing prices for user-specified portfolio constituents and benchmark (`SPY`) over trailing 252 trading days (1 market year).
  - Ticker sector classification and market capitalization.
- **Statistical Outputs**:
  - Daily Log Returns: $R_{i,t} = \ln\left(\frac{P_{i,t}}{P_{i,t-1}}\right)$
  - Annualized Volatility: $\sigma_i = \text{std}(R_i) \times \sqrt{252}$
  - Asset Covariance Matrix: $\mathbf{\Sigma} \in \mathbb{R}^{N \times N}$
  - Historical Beta: $\beta_i = \frac{\text{Cov}(R_i, R_{\text{SPY}})}{\text{Var}(R_{\text{SPY}})}$
- **Reliability Guarantee**: Cached in SQLite with a 24-hour TTL; pre-calculated matrices for default institutional portfolios ensure instantaneous offline responses.

---

## 8. Database Design

```sql
-- Raw Ingested Articles Table
CREATE TABLE articles (
    id VARCHAR(64) PRIMARY KEY, -- SHA-256 hash of title + timestamp
    source VARCHAR(32) NOT NULL, -- 'GDELT' or 'Kaggle'
    title TEXT NOT NULL,
    content TEXT,
    url TEXT,
    published_at TIMESTAMP NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Structured NLP Risk Signals Table
CREATE TABLE risk_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id VARCHAR(64) REFERENCES articles(id),
    ticker VARCHAR(12) NOT NULL,
    company_name VARCHAR(128),
    sentiment_score REAL NOT NULL, -- Normalized to [-1.0, +1.0]
    sentiment_label VARCHAR(16) NOT NULL, -- 'Positive', 'Negative', 'Neutral'
    event_type VARCHAR(64) NOT NULL, -- 8-class taxonomy
    event_confidence REAL NOT NULL, -- [0.0, 1.0]
    impact_score REAL NOT NULL, -- Scaled [1.0, 10.0]
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Portfolios Table
CREATE TABLE portfolios (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    total_value REAL NOT NULL, -- e.g. 10,000,000 USD
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Portfolio Positions Table
CREATE TABLE portfolio_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id VARCHAR(36) REFERENCES portfolios(id),
    ticker VARCHAR(12) NOT NULL,
    weight REAL NOT NULL, -- [0.0, 1.0], sum = 1.0
    shares REAL,
    sector VARCHAR(64)
);

-- Stress Testing Execution Audit Table
CREATE TABLE stress_test_runs (
    id VARCHAR(36) PRIMARY KEY,
    portfolio_id VARCHAR(36) REFERENCES portfolios(id),
    scenario_type VARCHAR(32) NOT NULL, -- 'HISTORICAL', 'NLP_SIGNAL', 'CUSTOM'
    scenario_name VARCHAR(128) NOT NULL,
    base_portfolio_value REAL NOT NULL,
    stressed_portfolio_value REAL NOT NULL,
    pnl_loss_amount REAL NOT NULL,
    pnl_loss_pct REAL NOT NULL,
    pre_var_95 REAL NOT NULL,
    post_var_95 REAL NOT NULL,
    pre_cvar_95 REAL NOT NULL,
    post_cvar_95 REAL NOT NULL,
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metrics_json TEXT NOT NULL
);
```

---

## 9. Backend API Design

All endpoints return standardized JSON payloads:

### Ingestion & Signals
- `GET /api/v1/health`  
  System status, loaded models, and DB connection status.
- `POST /api/v1/ingest/gdelt`  
  Triggers live GDELT DOC API harvest or loads cached offline records.
- `POST /api/v1/ingest/kaggle`  
  Ingests Kaggle financial dataset records from disk or uploaded CSV.
- `POST /api/v1/nlp/analyze`  
  Ad-hoc text inference endpoint: accepts raw text string, outputs entity, sentiment $[-1, 1]$, event type, and impact score $[1, 10]$.
- `GET /api/v1/signals`  
  Filters structured signals by `ticker`, `min_impact`, `event_type`, or `limit`.

### Portfolio & Module B Stress Testing
- `GET /api/v1/portfolio/default`  
  Retrieves standard $10M institutional multi-sector benchmark portfolio.
- `POST /api/v1/portfolio/custom`  
  Saves user-configured portfolio with weights and asset tickers.
- `GET /api/v1/market/stats?tickers=AAPL,JPM,NVDA`  
  Fetches covariance matrix, annualized volatilities, and asset betas.
- `POST /api/v1/stress-test/simulate`  
  Executes full stress simulation across Historical, NLP-driven, or Custom scenarios.
  - **Sample Request**:
    ```json
    {
      "portfolio_id": "default",
      "scenario": "NLP_NEWS_SHOCK",
      "signal_ids": [1, 4, 7],
      "custom_shocks": {"JPM": -0.15, "AAPL": -0.08},
      "confidence_level": 0.95
    }
    ```
  - **Sample Response**:
    ```json
    {
      "status": "success",
      "base_value": 10000000.0,
      "stressed_value": 9180000.0,
      "pnl_loss": -820000.0,
      "pnl_pct": -0.082,
      "pre_var_95": 142000.0,
      "post_var_95": 412000.0,
      "pre_cvar_95": 185000.0,
      "post_cvar_95": 548000.0,
      "asset_impacts": [
        {"ticker": "JPM", "shock": -0.15, "loss": -375000.0, "sector": "Financials"},
        {"ticker": "AAPL", "shock": -0.08, "loss": -200000.0, "sector": "Technology"}
      ],
      "recommendations": [
        "Hedge financial sector exposure via short XLF or protective puts.",
        "Rebalance overweight position in JPM (-15% shock scenario)."
      ]
    }
    ```

---

## 10. Frontend Architecture

### Visual & Functional Design
- **Theme**: High-contrast, institutional dark mode (`#0B0F17` background with slate/indigo accents).
- **Tab 1: Early Warning & Risk Engine**:
  - Live Ingestion Bar with status indicators for GDELT and Kaggle.
  - Real-time Signals Feed with color-coded badges:
    - Sentiment: Emerald ($> +0.3$), Slate ($-0.3$ to $+0.3$), Crimson ($< -0.3$).
    - Impact: Low (1-3), Moderate (4-6), High (7-8), Critical (9-10).
  - Interactive Text Tester allowing judges to paste any headline and inspect real-time inference.
- **Tab 2: Module B — Strategic Portfolio Stress Testing**:
  - Portfolio Configurator: Interactive weights slider and capital allocation editor.
  - Scenario Selector: Historical Presets (2008 Lehman, 2020 COVID, 2023 SVB) vs. Dynamic News Shock.
  - Visual Analytics Grid:
    - Waterfall P&L Chart showing loss attribution across holdings.
    - Return Distribution Curve showing baseline vs. stressed tail risk.
    - Contagion Heatmap showing sector spillover coefficients.

---

## 11. Portfolio Stress-Testing Methodology (Module B)

### 11.1. Signal-to-Shock Mapping Kernel
For asset $i$ mapped from risk signal $k$:

$$\Delta R_i^{\text{direct}} = \text{Sentiment}_k \times \left( \frac{\text{Impact}_k}{10} \right) \times \kappa_{\text{event}} \times \sigma_i$$

Where:
- $\text{Sentiment}_k \in [-1.0, +1.0]$ defines the shock direction.
- $\frac{\text{Impact}_k}{10} \in [0.1, 1.0]$ defines the shock amplitude.
- $\sigma_i$ is asset historical annualized volatility.
- $\kappa_{\text{event}}$ is the sensitivity coefficient (Credit = 2.5, Regulatory = 1.8, Earnings = 1.5, Governance = 1.2).

### 11.2. Cross-Asset Contagion Propagation
Portfolio assets not directly mentioned in the news receive indirect spillover shocks through their correlation with the shocked asset:

$$\Delta \mathbf{R}_{\text{portfolio}} = \mathbf{\Delta R}^{\text{direct}} + \mathbf{\Sigma} \cdot \mathbf{D}^{-1} \cdot \mathbf{\Delta R}^{\text{direct}} \cdot \gamma_{\text{contagion}}$$

Where $\mathbf{\Sigma}$ is the historical return covariance matrix, $\mathbf{D} = \text{diag}(\sigma_1^2, \dots, \sigma_N^2)$, and $\gamma_{\text{contagion}} \in [0.2, 0.4]$ is the dampening factor.

### 11.3. Value at Risk (VaR) & Expected Shortfall (CVaR)
- **1-Day Parametric VaR ($\alpha = 0.95, 0.99$)**:
  $$\text{VaR}_{\alpha} = V_{\text{portfolio}} \times \left( z_{\alpha} \cdot \sigma_p - \mu_p \right)$$
- **Stressed VaR**: Evaluated using post-shock return expectation and stressed covariance:
  $$\sigma_p^{\text{stressed}} = \sqrt{\mathbf{w}^T \mathbf{\Sigma}^{\text{stressed}} \mathbf{w}}$$
  $$\text{Stressed VaR}_{\alpha} = V_{\text{portfolio}} \times \left( z_{\alpha} \cdot \sigma_p^{\text{stressed}} - \mu_p^{\text{stressed}} \right)$$
- **Expected Shortfall (CVaR / Tail Loss)**:
  $$\text{CVaR}_{\alpha} = V_{\text{portfolio}} \times \left( \frac{\phi(z_{\alpha})}{1 - \alpha} \cdot \sigma_p - \mu_p \right)$$

---

## 12. Complete Folder Structure

```
c:/Users/Navya/OneDrive/Desktop/Teja/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI entry point & CORS configuration
│   │   ├── config.py                   # App settings, paths, environment variables
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── ingest.py               # GDELT & Kaggle ingestion routes
│   │   │   ├── nlp.py                  # Direct NLP inference & signals routes
│   │   │   ├── portfolio.py            # Portfolio management & market data routes
│   │   │   └── stress_test.py          # Module B simulation routes
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── database.py             # SQLite / SQLAlchemy session engine
│   │   │   └── models.py               # ORM models (articles, signals, portfolios)
│   │   ├── nlp/
│   │   │   ├── __init__.py
│   │   │   ├── preprocessor.py         # Regex, cleaning, normalization
│   │   │   ├── entity_extractor.py     # spaCy NER + Ticker/Sector resolver
│   │   │   ├── sentiment_engine.py     # FinBERT classifier wrapper
│   │   │   ├── event_classifier.py     # 8-class financial event categorizer
│   │   │   └── impact_scorer.py        # Impact calculation (1-10 scale)
│   │   ├── stress_engine/
│   │   │   ├── __init__.py
│   │   │   ├── market_data.py          # yfinance data ingestion & return calculator
│   │   │   ├── shock_mapper.py         # Translates NLP signals to asset return shocks
│   │   │   ├── risk_metrics.py         # VaR, CVaR, Monte Carlo & portfolio P&L
│   │   │   └── scenarios.py            # Historical presets (2008, 2020, SVB 2023)
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── nlp_schemas.py          # Pydantic models for text & signals
│   │       └── stress_schemas.py       # Pydantic models for portfolios & stress runs
│   ├── data/
│   │   ├── kaggle/
│   │   │   └── financial_news_sample.csv  # Curated Kaggle dataset records
│   │   ├── gdelt_cache/
│   │   │   └── sample_gdelt_feed.json     # Pre-cached fallback GDELT feed
│   │   └── app_database.db                # SQLite storage
│   ├── tests/
│   │   ├── test_nlp_engine.py          # Unit tests for NLP outputs
│   │   ├── test_stress_engine.py       # Unit tests for VaR/CVaR calculations
│   │   └── test_api.py                 # FastAPI integration tests
│   └── requirements.txt                # Python dependencies
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                     # Main layout & tab router
│       ├── index.css                   # Global styles & theme tokens
│       ├── types/
│       │   └── index.ts                # TypeScript interfaces (Signal, Portfolio, ShockResult)
│       ├── services/
│       │   └── api.ts                  # Axios/Fetch client for backend endpoints
│       ├── components/
│       │   ├── Navbar.tsx              # System status bar & navigation
│       │   ├── SignalBadge.tsx         # Color-coded Sentiment/Impact indicators
│       │   ├── NewsIngestSection.tsx   # GDELT & Kaggle feed controls
│       │   ├── SignalsTable.tsx        # Structured signals data grid
│       │   ├── PortfolioEditor.tsx     # Positions, weights, and capital input
│       │   ├── ScenarioSelector.tsx    # Preset & custom stress controls
│       │   ├── RiskMetricsCard.tsx     # VaR, CVaR, P&L display
│       │   ├── WaterfallChart.tsx      # Asset loss attribution chart
│       │   ├── VaRDistributionPlot.tsx # Return distribution curve
│       │   └── ContagionHeatmap.tsx    # Sector transmission matrix
│       └── utils/
│           └── formatters.ts           # Currency, percentage, and date formatters
│
├── run_all.bat                         # Windows one-click runner for both services
└── README.md                           # Documentation, setup guide, architecture review
```

---

## 13. Testing Strategy

1. **Mathematical Invariants**:
   - $\sum w_i = 1.0 \pm 10^{-5}$
   - $\text{CVaR}_{\alpha} \ge \text{VaR}_{\alpha}$ under every scenario (monotonic tail risk property).
   - $\text{Sentiment} \in [-1.0, +1.0]$ and $\text{Impact} \in [1.0, 10.0]$ strictly enforced.
2. **Network Resilience**:
   - GDELT API timeout falls back immediately to `backend/data/gdelt_cache/`.
   - `yfinance` failure falls back to pre-calculated covariance matrix.
3. **Automated Test Suite**:
   - `pytest backend/tests` validating all endpoints, Pydantic validations, and simulation math.

---

## 14. Deployment Strategy

- **Zero External Paid Dependencies**: Works out-of-the-box on Windows/Linux with standard Python 3.11 and Node.js 18+.
- **One-Click Orchestration**: A `run_all.bat` script starts the FastAPI server and Vite frontend concurrently.
- **Offline Self-Containment**: Hugging Face models and spaCy pipelines download once to local cache; pre-bundled dataset seeds ensure full functionality without live network.

---

## 15. Five-Minute Presentation & Demo Script

```
[0:00 - 1:00] PROBLEM INTRODUCTION & INGESTION
1. Introduce the platform: End-to-end AI Risk Engine & Portfolio Stress Testing System.
2. Trigger GDELT ingestion: Show live financial articles streaming into the system.
3. Ingest Kaggle dataset batch: Demonstrate multi-source deduplication and ingestion.

[1:00 - 2:15] CORE NLP RISK ENGINE
1. Walk through the Structured Signals Table:
   - Point out Sentiment Score normalized strictly between -1.0 and +1.0.
   - Point out Event Classification across 8 categories (Credit Distress, Earnings, etc.).
   - Point out calibrated Impact Score (1 to 10).
2. Live Ad-Hoc Text Analysis: Paste a breaking news headline into the interactive tester and demonstrate real-time entity resolution and signal extraction.

[2:15 - 3:45] MODULE B: STRATEGIC PORTFOLIO STRESS TESTING
1. Switch to Portfolio Stress Console.
2. Present the $10M multi-asset portfolio (AAPL, JPM, NVDA, XOM, JNJ).
3. Display baseline risk metrics: 1-Day 95% VaR = $142,000 | Expected Shortfall = $188,000.
4. Execute Dynamic NLP-Driven News Shock from the active news feed.
5. Review immediate impacts:
   - Portfolio Loss: -$820,000 (-8.2%).
   - Stressed 95% VaR increases to $412,000.
   - Waterfall chart reveals primary asset drivers.
   - Contagion matrix shows sector spillover effects.

[3:45 - 4:30] HISTORICAL CRISIS REPLAY & FACTOR WHAT-IF
1. Switch to the 2008 Lehman Brothers Liquidity Shock preset.
2. Adjust interest rate factor slider (+200 bps) and observe real-time distribution shift.

[4:30 - 5:00] CONCLUSION & CASE STUDY COMPLIANCE
1. Summarize compliance with all S&P Global × CRISIL requirements:
   - Two free text sources (GDELT + Kaggle).
   - FinBERT sentiment [-1, 1], event taxonomy, and impact score [1, 10].
   - Downstream Module B stress testing with yfinance market data.
   - Zero paid APIs, 100% reproducible and offline-resilient.
```

---

## 16. Case Study Requirement Traceability Matrix

| Requirement | Implementation Component | File Path |
| :--- | :--- | :--- |
| **Ingest unstructured text from at least 2 sources** | GDELT 2.0 API + Kaggle Financial News CSV | `backend/app/api/ingest.py`<br>`backend/data/kaggle/` |
| **Sentiment Score from $-1$ to $+1$** | `ProsusAI/finbert` scaled: $P(\text{pos}) - P(\text{neg})$ | `backend/app/nlp/sentiment_engine.py` |
| **Event Classification** | 8-Class financial event taxonomy classifier | `backend/app/nlp/event_classifier.py` |
| **Impact Score from $1$ to $10$** | Mathematical severity function factoring sentiment, event weight, and entity size | `backend/app/nlp/impact_scorer.py` |
| **Structured Risk Signals to Downstream Apps** | Standardized JSON schema via REST API and SQLite store | `backend/app/schemas/nlp_schemas.py`<br>`backend/app/api/nlp.py` |
| **Free Market Data** | `yfinance` daily adjusted closes and return calculations | `backend/app/stress_engine/market_data.py` |
| **Module B: Strategic Portfolio Stress Testing** | Full risk simulator: NLP-to-shock mapping, contagion, post-shock P&L, VaR (95%/99%), and CVaR | `backend/app/stress_engine/risk_metrics.py`<br>`backend/app/stress_engine/shock_mapper.py` |
| **No Paid APIs** | 100% open-source: spaCy, Hugging Face, yfinance, SQLite, React | Root project configuration |
