"""Initial schema for 8 core tables with indexes

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-03 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. news_documents
    op.create_table(
        'news_documents',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('source', sa.String(32), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('publication_time', sa.DateTime(), nullable=False),
        sa.Column('retrieved_time', sa.DateTime(), nullable=False),
        sa.Column('company_entities', sa.Text(), nullable=True),
        sa.Column('original_label', sa.String(64), nullable=True),
        sa.Column('domain', sa.String(128), nullable=True),
        sa.Column('language', sa.String(32), nullable=True),
        sa.Column('query_used', sa.String(256), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True)
    )
    op.create_index('ix_news_documents_source', 'news_documents', ['source'])
    op.create_index('ix_news_documents_pub_time', 'news_documents', ['publication_time'])

    # 2. companies
    op.create_table(
        'companies',
        sa.Column('ticker', sa.String(16), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('sector', sa.String(64), nullable=False),
        sa.Column('industry', sa.String(128), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_companies_sector', 'companies', ['sector'])

    # 3. index_constituents
    op.create_table(
        'index_constituents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('index_name', sa.String(64), nullable=False),
        sa.Column('ticker', sa.String(16), sa.ForeignKey('companies.ticker'), nullable=False),
        sa.Column('baseline_weight', sa.Float(), nullable=False),
        sa.Column('current_weight', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_index_constituents_ticker', 'index_constituents', ['ticker'])

    # 4. risk_signals
    op.create_table(
        'risk_signals',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('document_id', sa.String(64), sa.ForeignKey('news_documents.id'), nullable=True),
        sa.Column('article_id', sa.String(64), nullable=True),
        sa.Column('company', sa.String(16), nullable=False),
        sa.Column('ticker', sa.String(16), nullable=False),
        sa.Column('company_name', sa.String(128), nullable=True),
        sa.Column('sector', sa.String(64), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=False),
        sa.Column('sentiment_label', sa.String(16), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('event_confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('impact_score', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(16), nullable=False, default='MEDIUM'),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('source', sa.String(32), nullable=False, default='GDELT'),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_risk_signals_company', 'risk_signals', ['company'])
    op.create_index('ix_risk_signals_source', 'risk_signals', ['source'])
    op.create_index('ix_risk_signals_event_type', 'risk_signals', ['event_type'])
    op.create_index('ix_risk_signals_timestamp', 'risk_signals', ['timestamp'])
    op.create_index('ix_risk_signals_impact', 'risk_signals', ['impact_score'])

    # 5. market_data_records
    op.create_table(
        'market_data_records',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('ticker', sa.String(16), sa.ForeignKey('companies.ticker'), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('previous_close', sa.Float(), nullable=True),
        sa.Column('change_pct', sa.Float(), nullable=True),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.Column('volatility_annual', sa.Float(), nullable=True),
        sa.Column('beta', sa.Float(), default=1.0),
        sa.Column('as_of', sa.DateTime(), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_market_data_ticker', 'market_data_records', ['ticker'])
    op.create_index('ix_market_data_as_of', 'market_data_records', ['as_of'])

    # 6. rebalance_runs
    op.create_table(
        'rebalance_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('universe_size', sa.Integer(), nullable=False),
        sa.Column('turnover_pct', sa.Float(), nullable=False),
        sa.Column('total_current_weight_pct', sa.Float(), nullable=False),
        sa.Column('total_target_weight_pct', sa.Float(), nullable=False),
        sa.Column('average_sentiment', sa.Float(), nullable=False),
        sa.Column('average_impact', sa.Float(), nullable=False),
        sa.Column('methodology', sa.Text(), nullable=True)
    )
    op.create_index('ix_rebalance_runs_time', 'rebalance_runs', ['timestamp'])

    # 7. rebalance_decisions
    op.create_table(
        'rebalance_decisions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('rebalance_runs.id'), nullable=False),
        sa.Column('ticker', sa.String(16), nullable=False),
        sa.Column('company_name', sa.String(128), nullable=True),
        sa.Column('current_weight', sa.Float(), nullable=False),
        sa.Column('target_weight', sa.Float(), nullable=False),
        sa.Column('weight_delta_pct', sa.Float(), nullable=False),
        sa.Column('action', sa.String(16), nullable=False),
        sa.Column('sentiment_score', sa.Float(), nullable=False),
        sa.Column('impact_score', sa.Float(), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False)
    )
    op.create_index('ix_rebalance_decisions_run', 'rebalance_decisions', ['run_id'])
    op.create_index('ix_rebalance_decisions_ticker', 'rebalance_decisions', ['ticker'])

    # 8. data_source_logs
    op.create_table(
        'data_source_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.String(32), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('record_count', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Float(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('query_used', sa.String(256), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_data_source_logs_source', 'data_source_logs', ['source'])
    op.create_index('ix_data_source_logs_status', 'data_source_logs', ['status'])
    op.create_index('ix_data_source_logs_timestamp', 'data_source_logs', ['timestamp'])

def downgrade() -> None:
    op.drop_table('data_source_logs')
    op.drop_table('rebalance_decisions')
    op.drop_table('rebalance_runs')
    op.drop_table('market_data_records')
    op.drop_table('risk_signals')
    op.drop_table('index_constituents')
    op.drop_table('companies')
    op.drop_table('news_documents')
