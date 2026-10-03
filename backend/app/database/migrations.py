import logging
from sqlalchemy import text, inspect
from backend.app.database.connection import engine, Base, SessionLocal
from backend.app.database import models
from backend.app.portfolio.market_data import MarketDataService

logger = logging.getLogger("database.migrations")

def run_migrations():
    """
    Executes schema migrations and initializes all 8 required tables:
    1. news_documents (NewsDocument)
    2. risk_signals (RiskSignal)
    3. companies (Company)
    4. index_constituents (IndexConstituent)
    5. market_data_records (MarketData)
    6. rebalance_runs (RebalanceRun)
    7. rebalance_decisions (RebalanceDecision)
    8. data_source_logs (DataSourceLog)
    
    Creates explicit performance indexes for:
    - company / ticker
    - timestamp / publication_time
    - source
    - event_type
    """
    logger.info("[Migrations] Creating / verifying all 8 database tables...")
    Base.metadata.create_all(bind=engine)

    # Inspect and apply column/index migrations to existing SQLite/Postgres tables
    insp = inspect(engine)
    with engine.connect() as conn:
        # Check risk_signals columns
        existing_cols = {c["name"] for c in insp.get_columns("risk_signals")}
        
        # Add company column if missing
        if "company" not in existing_cols:
            logger.info("[Migrations] Adding 'company' column to risk_signals...")
            conn.execute(text("ALTER TABLE risk_signals ADD COLUMN company VARCHAR(16) DEFAULT 'GENERAL'"))
            conn.execute(text("UPDATE risk_signals SET company = ticker WHERE ticker IS NOT NULL"))

        # Add risk_level column if missing
        if "risk_level" not in existing_cols:
            logger.info("[Migrations] Adding 'risk_level' column to risk_signals...")
            conn.execute(text("ALTER TABLE risk_signals ADD COLUMN risk_level VARCHAR(16) DEFAULT 'MEDIUM'"))

        # Add source column if missing
        if "source" not in existing_cols:
            logger.info("[Migrations] Adding 'source' column to risk_signals...")
            conn.execute(text("ALTER TABLE risk_signals ADD COLUMN source VARCHAR(32) DEFAULT 'GDELT'"))

        # Add timestamp column if missing
        if "timestamp" not in existing_cols:
            logger.info("[Migrations] Adding 'timestamp' column to risk_signals...")
            conn.execute(text("ALTER TABLE risk_signals ADD COLUMN timestamp DATETIME"))
            conn.execute(text("UPDATE risk_signals SET timestamp = created_at WHERE created_at IS NOT NULL"))

        # Add explanation column if missing
        if "explanation" not in existing_cols:
            logger.info("[Migrations] Adding 'explanation' column to risk_signals...")
            conn.execute(text("ALTER TABLE risk_signals ADD COLUMN explanation TEXT"))
            conn.execute(text("UPDATE risk_signals SET explanation = summary WHERE summary IS NOT NULL"))

        # Add document_id column if missing
        if "document_id" not in existing_cols:
            logger.info("[Migrations] Adding 'document_id' column to risk_signals...")
            conn.execute(text("ALTER TABLE risk_signals ADD COLUMN document_id VARCHAR(64)"))
            conn.execute(text("UPDATE risk_signals SET document_id = article_id WHERE article_id IS NOT NULL"))

        # Add sector column if missing
        if "sector" not in existing_cols:
            logger.info("[Migrations] Adding 'sector' column to risk_signals...")
            conn.execute(text("ALTER TABLE risk_signals ADD COLUMN sector VARCHAR(64) DEFAULT 'General'"))

        conn.commit()

        # Create requested performance indexes
        logger.info("[Migrations] Verifying and creating required indexes...")
        index_queries = [
            # 1. Company / Ticker index
            "CREATE INDEX IF NOT EXISTS ix_risk_signals_company ON risk_signals (company)",
            "CREATE INDEX IF NOT EXISTS ix_risk_signals_ticker ON risk_signals (ticker)",
            "CREATE INDEX IF NOT EXISTS ix_companies_sector ON companies (sector)",
            "CREATE INDEX IF NOT EXISTS ix_index_constituents_ticker ON index_constituents (ticker)",
            "CREATE INDEX IF NOT EXISTS ix_market_data_ticker ON market_data_records (ticker)",
            "CREATE INDEX IF NOT EXISTS ix_rebalance_decisions_ticker ON rebalance_decisions (ticker)",

            # 2. Timestamp index
            "CREATE INDEX IF NOT EXISTS ix_risk_signals_timestamp ON risk_signals (timestamp)",
            "CREATE INDEX IF NOT EXISTS ix_news_documents_pub_time ON news_documents (publication_time)",
            "CREATE INDEX IF NOT EXISTS ix_news_documents_retrieved_time ON news_documents (retrieved_time)",
            "CREATE INDEX IF NOT EXISTS ix_market_data_as_of ON market_data_records (as_of)",
            "CREATE INDEX IF NOT EXISTS ix_rebalance_runs_time ON rebalance_runs (timestamp)",
            "CREATE INDEX IF NOT EXISTS ix_data_source_logs_time ON data_source_logs (timestamp)",

            # 3. Source index
            "CREATE INDEX IF NOT EXISTS ix_risk_signals_source ON risk_signals (source)",
            "CREATE INDEX IF NOT EXISTS ix_news_documents_source ON news_documents (source)",
            "CREATE INDEX IF NOT EXISTS ix_data_source_logs_source ON data_source_logs (source)",

            # 4. Event Type index
            "CREATE INDEX IF NOT EXISTS ix_risk_signals_event_type ON risk_signals (event_type)",
            "CREATE INDEX IF NOT EXISTS ix_rebalance_decisions_event_type ON rebalance_decisions (event_type)",

            # Composite query indexes
            "CREATE INDEX IF NOT EXISTS ix_risk_signals_company_time ON risk_signals (company, timestamp)",
            "CREATE INDEX IF NOT EXISTS ix_risk_signals_event_impact ON risk_signals (event_type, impact_score)"
        ]

        for q in index_queries:
            try:
                conn.execute(text(q))
            except Exception as ie:
                logger.debug(f"[Migrations] Index execution note: {ie}")
        conn.commit()

    logger.info("[Migrations] Tables and indexes initialized successfully.")

    # Seed the 15 mock index companies if companies table is empty
    db = SessionLocal()
    try:
        existing_companies = db.query(models.Company).count()
        if existing_companies == 0:
            logger.info("[Migrations] Seeding 15 mock index companies into database...")
            universe = MarketDataService.DEFAULT_INDEX_UNIVERSE
            base_w = round(1.0 / len(universe), 4)

            for ticker, info in universe.items():
                comp = models.Company(
                    ticker=ticker,
                    name=info["name"],
                    sector=info["sector"],
                    is_active=True
                )
                db.add(comp)

                constituent = models.IndexConstituent(
                    index_name="S&P x CRISIL 15",
                    ticker=ticker,
                    baseline_weight=base_w,
                    current_weight=base_w,
                    is_active=True
                )
                db.add(constituent)

            db.commit()
            logger.info(f"[Migrations] Successfully seeded {len(universe)} companies and index constituents.")
    except Exception as e:
        db.rollback()
        logger.error(f"[Migrations] Error seeding companies: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migrations()
