import React from 'react';
import { 
  Sparkles, 
  ArrowUpRight, 
  ArrowDownRight, 
  AlertTriangle, 
  Clock, 
  Layers, 
  RefreshCw, 
  Database,
  ShieldCheck,
  TrendingUp
} from 'lucide-react';
import type { RebalanceSummary, RiskSignalItem } from '../types';

interface OverviewSectionProps {
  rebalanceSummary: RebalanceSummary | null;
  signals: RiskSignalItem[];
  lastIngestionTime: string | null;
  onIngestGdelt: () => void;
  onIngestKaggle: () => void;
  isIngesting: boolean;
}

export const OverviewSection: React.FC<OverviewSectionProps> = ({
  rebalanceSummary,
  signals,
  lastIngestionTime,
  onIngestGdelt,
  onIngestKaggle,
  isIngesting
}) => {
  const trackedStocksCount = rebalanceSummary?.universe_size || 15;
  const totalSignals = signals.length;
  const positiveSignals = signals.filter(s => s.sentiment_score > 0.05).length;
  const negativeSignals = signals.filter(s => s.sentiment_score < -0.05).length;
  const highImpactEvents = signals.filter(s => s.impact_score >= 6.5).length;

  const formatTime = (isoString?: string | null) => {
    if (!isoString) return 'Real-time / Just now';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + 
        ' (' + d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ')';
    } catch {
      return isoString;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      
      {/* Banner / Pipeline Control Ribbon */}
      <div className="card" style={{
        padding: '1rem 1.25rem',
        background: 'linear-gradient(90deg, rgba(6, 182, 212, 0.08) 0%, rgba(13, 20, 36, 0.85) 60%)',
        borderColor: 'rgba(6, 182, 212, 0.25)',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: 'rgba(6, 182, 212, 0.15)',
            border: '1px solid rgba(6, 182, 212, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-cyan)'
          }}>
            <Sparkles size={18} />
          </div>
          <div>
            <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#FFFFFF' }}>
              Module A Tactical Engine Active &bull; S&P Global x CRISIL 15-Stock Universe
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              Directional FinBERT sentiment [-1, +1] combined with 10-class event taxonomy and water-filling allocation bounds (2% floor, 15% cap).
            </div>
          </div>
        </div>

        {/* Action Triggers */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <button
            onClick={onIngestGdelt}
            disabled={isIngesting}
            className="btn btn-secondary"
            title="Poll real-time GDELT Project v2 API"
          >
            <RefreshCw size={13} style={{ color: 'var(--color-cyan)' }} className={isIngesting ? 'animate-spin' : ''} />
            <span>Poll GDELT Live</span>
          </button>

          <button
            onClick={onIngestKaggle}
            disabled={isIngesting}
            className="btn btn-secondary"
            title="Ingest verified Kaggle Financial News PhraseBank corpus"
          >
            <Database size={13} style={{ color: 'var(--color-indigo)' }} />
            <span>Ingest Kaggle News</span>
          </button>
        </div>
      </div>

      {/* 7 Core KPI Cards */}
      <div className="kpi-row">
        
        {/* 1. Tracked Stocks */}
        <div className="kpi-card kpi-cyan">
          <div className="kpi-label">
            <span>Tracked Stocks</span>
            <Layers size={13} style={{ color: 'var(--color-cyan)' }} />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">{trackedStocksCount}</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', fontFamily: 'monospace' }}>STOCKS</span>
          </div>
          <div className="kpi-subtext">100% Target Sum</div>
        </div>

        {/* 2. Total Signals */}
        <div className="kpi-card kpi-indigo">
          <div className="kpi-label">
            <span>Total Signals</span>
            <ShieldCheck size={13} style={{ color: 'var(--color-indigo)' }} />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">{totalSignals}</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--color-indigo)', fontFamily: 'monospace' }}>ANALYZED</span>
          </div>
          <div className="kpi-subtext">Canonical Schema</div>
        </div>

        {/* 3. Positive Signals */}
        <div className="kpi-card kpi-emerald">
          <div className="kpi-label" style={{ color: 'var(--color-emerald)' }}>
            <span>Positive</span>
            <ArrowUpRight size={14} style={{ color: 'var(--color-emerald)' }} />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value" style={{ color: '#34D399' }}>{positiveSignals}</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              {totalSignals > 0 ? `${((positiveSignals / totalSignals) * 100).toFixed(0)}%` : '0%'}
            </span>
          </div>
          <div className="kpi-subtext">Bullish Catalysts</div>
        </div>

        {/* 4. Negative Signals */}
        <div className="kpi-card kpi-rose">
          <div className="kpi-label" style={{ color: 'var(--color-rose)' }}>
            <span>Negative</span>
            <ArrowDownRight size={14} style={{ color: 'var(--color-rose)' }} />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value" style={{ color: '#FB7185' }}>{negativeSignals}</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              {totalSignals > 0 ? `${((negativeSignals / totalSignals) * 100).toFixed(0)}%` : '0%'}
            </span>
          </div>
          <div className="kpi-subtext">Risk / Shocks</div>
        </div>

        {/* 5. High-Impact Events */}
        <div className="kpi-card kpi-amber">
          <div className="kpi-label" style={{ color: 'var(--color-amber)' }}>
            <span>High Impact</span>
            <AlertTriangle size={13} style={{ color: 'var(--color-amber)' }} />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value" style={{ color: '#FBBF24' }}>{highImpactEvents}</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>&ge; 6.5</span>
          </div>
          <div className="kpi-subtext">Severe Market Shocks</div>
        </div>

        {/* 6. Last Ingestion Time */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Last Ingestion</span>
            <Clock size={13} style={{ color: 'var(--text-tertiary)' }} />
          </div>
          <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {formatTime(lastIngestionTime)}
          </div>
          <div className="kpi-subtext">Automated Ingestion</div>
        </div>

        {/* 7. Last Rebalance Time */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Last Rebalance</span>
            <TrendingUp size={13} style={{ color: 'var(--color-emerald)' }} />
          </div>
          <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', fontWeight: 700, color: '#34D399', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {formatTime(rebalanceSummary?.as_of)}
          </div>
          <div className="kpi-subtext font-mono">
            Turnover: {rebalanceSummary ? `${rebalanceSummary.turnover_pct.toFixed(2)}%` : '0.00%'}
          </div>
        </div>

      </div>

    </div>
  );
};
