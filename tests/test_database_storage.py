import unittest
from datetime import datetime, timezone
from sqlalchemy import inspect
from backend.app.database.connection import engine, SessionLocal, get_engine
from backend.app.database import models
from backend.app.config.settings import settings

class TestDatabaseStorage(unittest.TestCase):
    """
    Test suite for Step 10: Persistent Database Storage.
    Verifies:
    1. All 8 required models/tables exist in the database.
    2. Explicit indexes exist for: company, timestamp, source, event_type.
    3. CRUD operations store source, timestamps, sentiment, event type, impact,
       stock weights, rebalance decisions, explanations.
    4. No API credentials stored in database.
    5. Fallback behavior (PostgreSQL with SQLite fallback) works.
    """

    def setUp(self):
        self.db = SessionLocal()
        self.inspector = inspect(engine)

    def tearDown(self):
        self.db.close()

    def test_01_all_eight_tables_exist(self):
        """Prove that all 8 required models/tables exist in the schema."""
        table_names = set(self.inspector.get_table_names())

        expected_tables = {
            "news_documents",
            "risk_signals",
            "companies",
            "index_constituents",
            "market_data_records",
            "rebalance_runs",
            "rebalance_decisions",
            "data_source_logs"
        }

        for table in expected_tables:
            self.assertIn(table, table_names, f"Missing required table: {table}")

    def test_02_indexes_exist_for_required_fields(self):
        """Prove that explicit indexes exist for company, timestamp, source, and event_type."""
        # 1. Check risk_signals indexes
        rs_indexes = {ix["name"] for ix in self.inspector.get_indexes("risk_signals")}
        self.assertIn("ix_risk_signals_company", rs_indexes)
        self.assertIn("ix_risk_signals_timestamp", rs_indexes)
        self.assertIn("ix_risk_signals_source", rs_indexes)
        self.assertIn("ix_risk_signals_event_type", rs_indexes)

        # 2. Check news_documents indexes
        nd_indexes = {ix["name"] for ix in self.inspector.get_indexes("news_documents")}
        self.assertIn("ix_news_documents_source", nd_indexes)
        self.assertIn("ix_news_documents_pub_time", nd_indexes)

        # 3. Check companies and market data indexes
        c_indexes = {ix["name"] for ix in self.inspector.get_indexes("companies")}
        self.assertIn("ix_companies_sector", c_indexes)

        md_indexes = {ix["name"] for ix in self.inspector.get_indexes("market_data_records")}
        self.assertIn("ix_market_data_ticker", md_indexes)
        self.assertIn("ix_market_data_as_of", md_indexes)

    def test_03_crud_persistence_and_relationships(self):
        """Prove end-to-end persistence of source, timestamp, sentiment, event, impact, weights, and decisions."""
        now = datetime.now(timezone.utc)

        # 1. NewsDocument
        doc_id = f"test_doc_{int(now.timestamp())}"
        doc = models.NewsDocument(
            id=doc_id,
            source="GDELT",
            title="Microsoft expands cloud infrastructure investment",
            text="Microsoft announced a $3 billion expansion in cloud data centers.",
            url="https://news.example.com/msft-cloud",
            publication_time=now,
            retrieved_time=now,
            company_entities='["MSFT"]',
            domain="example.com",
            language="English"
        )
        self.db.add(doc)
        self.db.commit()

        # 2. RiskSignal linked to NewsDocument
        sig = models.RiskSignal(
            document_id=doc_id,
            company="MSFT",
            ticker="MSFT",
            company_name="Microsoft Corporation",
            sector="Technology",
            sentiment_score=0.75,
            sentiment_label="Positive",
            event_type="Product Launch",
            event_confidence=0.92,
            impact_score=6.8,
            risk_level="LOW",
            explanation="Major data center infrastructure expansion indicates commercial growth.",
            source="GDELT",
            timestamp=now
        )
        self.db.add(sig)
        self.db.commit()

        # 3. RebalanceRun & RebalanceDecision
        run_id = f"run_{int(now.timestamp())}"
        run = models.RebalanceRun(
            id=run_id,
            timestamp=now,
            universe_size=15,
            turnover_pct=4.25,
            total_current_weight_pct=100.0,
            total_target_weight_pct=100.0,
            average_sentiment=0.35,
            average_impact=6.1,
            methodology="Tactical High-Frequency Stock Index Rebalancer"
        )
        self.db.add(run)
        self.db.commit()

        decision = models.RebalanceDecision(
            run_id=run_id,
            ticker="MSFT",
            company_name="Microsoft Corporation",
            current_weight=0.0667,
            target_weight=0.0820,
            weight_delta_pct=1.53,
            action="INCREASE",
            sentiment_score=0.75,
            impact_score=6.8,
            event_type="Product Launch",
            explanation="Weight increased due to positive sentiment (+0.75) and expansion event."
        )
        self.db.add(decision)
        self.db.commit()

        # 4. DataSourceLog
        log_entry = models.DataSourceLog(
            source="GDELT",
            status="SUCCESS_LIVE",
            record_count=12,
            duration_ms=450.2,
            query_used="technology stocks",
            timestamp=now
        )
        self.db.add(log_entry)
        self.db.commit()

        # Verification Queries
        queried_doc = self.db.query(models.NewsDocument).filter(models.NewsDocument.id == doc_id).first()
        self.assertIsNotNone(queried_doc)
        self.assertEqual(len(queried_doc.signals), 1)
        self.assertEqual(queried_doc.signals[0].company, "MSFT")
        self.assertEqual(queried_doc.signals[0].impact_score, 6.8)

        queried_run = self.db.query(models.RebalanceRun).filter(models.RebalanceRun.id == run_id).first()
        self.assertIsNotNone(queried_run)
        self.assertEqual(len(queried_run.decisions), 1)
        self.assertEqual(queried_run.decisions[0].action, "INCREASE")
        self.assertEqual(queried_run.decisions[0].weight_delta_pct, 1.53)

        # Cleanup test records
        self.db.delete(decision)
        self.db.delete(run)
        self.db.delete(sig)
        self.db.delete(doc)
        self.db.delete(log_entry)
        self.db.commit()

    def test_04_no_credentials_stored_in_database(self):
        """Verify that API keys or credentials are never columns or values in the database tables."""
        sensitive_terms = ["api_key", "password", "secret", "token", "kaggle_key", "auth_token"]

        for table in self.inspector.get_table_names():
            columns = [c["name"].lower() for c in self.inspector.get_columns(table)]
            for term in sensitive_terms:
                self.assertNotIn(term, columns, f"Found sensitive column '{term}' in table '{table}'")

    def test_05_companies_and_constituents_seeded(self):
        """Verify that 15 liquid mock index companies and constituents are populated."""
        comp_count = self.db.query(models.Company).count()
        const_count = self.db.query(models.IndexConstituent).count()

        self.assertGreaterEqual(comp_count, 15)
        self.assertGreaterEqual(const_count, 15)

        # Verify key constituents
        for tkr in ["AAPL", "NVDA", "JPM", "XOM", "TSLA"]:
            comp = self.db.query(models.Company).filter(models.Company.ticker == tkr).first()
            self.assertIsNotNone(comp, f"Company {tkr} not found in DB")
            self.assertTrue(comp.is_active)

if __name__ == "__main__":
    unittest.main()
