import React from 'react';
import { 
  ArrowUpRight, 
  ArrowDownRight, 
  Minus, 
  Cpu, 
  ShieldCheck, 
  TrendingUp, 
  TrendingDown
} from 'lucide-react';
import type { ConstituentRebalanceDetail } from '../types';

interface SignalExplanationCardProps {
  constituent: ConstituentRebalanceDetail | null;
}

export const SignalExplanationCard: React.FC<SignalExplanationCardProps> = ({ constituent }) => {
  if (!constituent) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
        Select a stock from the index table to view its explainable signal attribution.
      </div>
    );
  }

  const isIncrease = constituent.rebalance_action === 'INCREASE';
  const isReduce = constituent.rebalance_action === 'REDUCE';

  return (
    <div className="card" style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '1rem',
      borderColor: isIncrease ? 'rgba(16, 185, 129, 0.35)' : isReduce ? 'rgba(244, 63, 94, 0.35)' : 'var(--border-medium)',
      background: isIncrease 
        ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(13, 20, 36, 0.9) 100%)'
        : isReduce 
        ? 'linear-gradient(135deg, rgba(244, 63, 94, 0.05) 0%, rgba(13, 20, 36, 0.9) 100%)'
        : 'var(--glass-bg)'
    }}>
      
      {/* Header */}
      <div className="card-header" style={{ margin: 0 }}>
        <div className="card-title-group">
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '10px',
            background: isIncrease ? 'rgba(16, 185, 129, 0.15)' : isReduce ? 'rgba(244, 63, 94, 0.15)' : 'rgba(100, 116, 139, 0.15)',
            border: isIncrease ? '1px solid rgba(16, 185, 129, 0.4)' : isReduce ? '1px solid rgba(244, 63, 94, 0.4)' : '1px solid rgba(100, 116, 139, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: isIncrease ? '#34D399' : isReduce ? '#FB7185' : 'var(--text-secondary)'
          }}>
            {isIncrease ? <ArrowUpRight size={20} /> : isReduce ? <ArrowDownRight size={20} /> : <Minus size={20} />}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="font-mono" style={{ fontSize: '1.05rem', fontWeight: 800, color: '#FFFFFF' }}>{constituent.ticker}</span>
              <span style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', fontWeight: 600 }}>{constituent.company_name}</span>
              <span className={`badge ${isIncrease ? 'badge-emerald' : isReduce ? 'badge-rose' : 'badge-slate'}`} style={{ fontSize: '0.68rem' }}>
                {constituent.rebalance_action}
              </span>
            </div>
            <div className="card-subtitle">
              Signal Attribution & Tactical Allocation Rationale
            </div>
          </div>
        </div>

        {/* Transition Tag */}
        <div className="font-mono" style={{
          padding: '0.35rem 0.75rem',
          borderRadius: '8px',
          background: 'var(--bg-input)',
          border: '1px solid var(--border-subtle)',
          fontSize: '0.75rem'
        }}>
          <span style={{ color: 'var(--text-tertiary)' }}>Base: {constituent.current_weight_pct.toFixed(2)}%</span>
          <span style={{ margin: '0 0.35rem', color: 'var(--text-tertiary)' }}>&rarr;</span>
          <span style={{ color: '#FFFFFF', fontWeight: 700 }}>Target: {constituent.target_weight_pct.toFixed(2)}%</span>
          <span style={{ marginLeft: '0.45rem', fontWeight: 800, color: isIncrease ? '#34D399' : isReduce ? '#FB7185' : 'var(--text-tertiary)' }}>
            ({constituent.weight_delta_pct >= 0 ? '+' : ''}{constituent.weight_delta_pct.toFixed(2)}%)
          </span>
        </div>
      </div>

      {/* 4 Core Quantitative Decision Factors */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: '0.75rem'
      }}>
        
        {/* Factor 1: Sentiment */}
        <div style={{ background: 'var(--bg-input)', padding: '0.75rem 0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>1. Sentiment Score</div>
          <div className="font-mono" style={{
            fontSize: '1.2rem',
            fontWeight: 800,
            marginTop: '0.25rem',
            color: constituent.latest_sentiment_score > 0.05 ? '#34D399' : constituent.latest_sentiment_score < -0.05 ? '#FB7185' : 'var(--text-secondary)'
          }}>
            {constituent.latest_sentiment_score >= 0 ? '+' : ''}{constituent.latest_sentiment_score.toFixed(2)}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>Range: [-1.0, +1.0]</div>
        </div>

        {/* Factor 2: Impact Score */}
        <div style={{ background: 'var(--bg-input)', padding: '0.75rem 0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>2. Impact Rating</div>
          <div className="font-mono" style={{
            fontSize: '1.2rem',
            fontWeight: 800,
            marginTop: '0.25rem',
            color: constituent.latest_impact_score >= 7.5 ? '#FB7185' : constituent.latest_impact_score >= 5.0 ? '#FBBF24' : 'var(--color-cyan)'
          }}>
            {constituent.latest_impact_score.toFixed(1)}/10
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>5-Factor Calibrated</div>
        </div>

        {/* Factor 3: Event Taxonomy */}
        <div style={{ background: 'var(--bg-input)', padding: '0.75rem 0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>3. Event Taxonomy</div>
          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#FFFFFF', marginTop: '0.4rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {constituent.latest_event_type}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>10-Class Taxonomy</div>
        </div>

        {/* Factor 4: Tactical Action */}
        <div style={{ background: 'var(--bg-input)', padding: '0.75rem 0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>4. Action Signal</div>
          <div className="font-mono" style={{
            fontSize: '1.1rem',
            fontWeight: 800,
            marginTop: '0.25rem',
            color: isIncrease ? '#34D399' : isReduce ? '#FB7185' : 'var(--text-secondary)'
          }}>
            {constituent.rebalance_action}
          </div>
          <div className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>
            Signal: {constituent.calculated_risk_signal >= 0 ? '+' : ''}{constituent.calculated_risk_signal.toFixed(3)}
          </div>
        </div>

      </div>

      {/* Narrative Explanation */}
      <div style={{
        background: 'var(--bg-input)',
        padding: '1rem',
        borderRadius: '10px',
        border: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-cyan)' }}>
          <Cpu size={15} />
          <span>Decision Reason & Transparent Explanation:</span>
        </div>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', lineHeight: 1.6, fontStyle: 'italic', margin: 0 }}>
          "{constituent.explanation}"
        </p>

        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.72rem',
          color: 'var(--text-tertiary)',
          paddingTop: '0.5rem',
          borderTop: '1px solid var(--border-subtle)',
          marginTop: '0.25rem'
        }}>
          <span className="font-mono">
            Target = Base(6.67%) + Signal({constituent.calculated_risk_signal >= 0 ? '+' : ''}{constituent.calculated_risk_signal.toFixed(3)}) &times; Scaling(3.5%) &rarr; Constrained [2.0% - 15.0%]
          </span>
          <span style={{ color: 'var(--color-cyan)', fontWeight: 600 }}>Zero Black-Box Allocation</span>
        </div>
      </div>

    </div>
  );
};
