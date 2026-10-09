# Data directory

- `sample_financial_news.csv` contains clearly labelled **synthetic example headlines** for inspecting the expected input schema. These are not real news articles and must not be presented as factual reporting.
- The active ingestion endpoints retrieve public news from GDELT and the configured public Financial PhraseBank mirror, then cache downloaded data locally.
- Market quotes/history are requested through yfinance and may be cached.
- Runtime cache files and the local SQLite database are intentionally excluded from version control to avoid committing machine-specific or changing data.
- No confidential S&P Global or CRISIL client data is used.
