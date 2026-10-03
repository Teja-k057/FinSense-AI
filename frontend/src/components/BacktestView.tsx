import React, { useState, useEffect } from 'react';
import { 
  BarChart, 
  RotateCw, 
  Info, 
  TrendingUp, 
  TrendingDown, 
  CheckCircle2 
} from 'lucide-react';
import { runHistoricalBacktest } from '../services/api';
import type { BacktestComparisonResult } from '../types';

export const BacktestView: React.FC = () => {
  const [backtestResult, setBacktestResult] = useState<BacktestComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [frequency, setFrequency] = useState<'WEEKLY' | 'DAILY' | 'MONTHLY'>('WEEKLY');
  const [timeframe, setTimeframe] = useState<'1M' | '3M' | '6M'>('1M');

  useEffect(() => {
    executeBacktest();
  }, [frequency, timeframe]);

  const executeBacktest = async () => {
    setLoading(true);
    setError(null);
    try {
      const endDate = new Date();
      const startDate = new Date();
      if (timeframe === '1M') startDate.setMonth(endDate.getMonth() - 1);
      else if (timeframe === '3M') startDate.setMonth(endDate.getMonth() - 3);
      else startDate.setMonth(endDate.getMonth() - 6);

      const result = await runHistoricalBacktest({
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
        rebalance_frequency: frequency
      });
      setBacktestResult(result);
    } catch (err: any) {
      console.error('Backtest error:', err);
      setError(err.message || 'Backtest failed to execute.');
    } finally {
      setLoading(false);
    }
  };

  const trajectory = backtestResult?.trajectory || [];
  const baseline = backtestResult?.baseline_metrics;
  const nlp = backtestResult?.nlp_strategy_metrics;

  const allReturns = trajectory.flatMap(p => [
    p.baseline_cumulative_return_pct, 
    p.nlp_cumulative_return_pct
  ]);
  const minVal = allReturns.length > 0 ? Math.min(...allReturns, 0) : -5;
  const maxVal = allReturns.length > 0 ? Math.max(...allReturns, 1) : 5;
  const range = (maxVal - minVal) || 1;

  const generatePath = (key: 'baseline_cumulative_return_pct' | 'nlp_cumulative_return_pct') => {
    if (trajectory.length < 2) return '';
    const width = 800;
    const height = 180;
    const stepX = width / (trajectory.length - 1);

    return trajectory.map((p, idx) => {
      const x = idx * stepX;
      const y = height - ((p[key] - minVal) / range) * height;
      return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(' ');
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* Header and Controls */}
      <div className="card-header">
        <div className="card-title-group">
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'rgba(6, 182, 212, 0.15)',
            border: '1px solid rgba(6, 182, 212, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-cyan)'
          }}>
            <BarChart size={16} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="card-title">Historical Backtest Simulator (Module A)</span>
              <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>Strict Anti-Look-Ahead Bias</span>
            </div>
            <div className="card-subtitle">
              Simulates baseline Equal-Weight mock index versus NLP Tactical Strategy with 10 bps transaction fees.
            </div>
          </div>
        </div>

        {/* Simulation Controls */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
          
          {/* Timeframe Buttons */}
          <div style={{ display: 'flex', background: 'var(--bg-input)', padding: '0.2rem', borderRadius: '8px', border: '1px solid var(--border-medium)' }}>
            {(['1M', '3M', '6M'] as const).map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                style={{
                  background: timeframe === tf ? 'var(--color-cyan)' : 'transparent',
                  color: timeframe === tf ? 'var(--text-inverse)' : 'var(--text-secondary)',
                  fontWeight: 700,
                  fontSize: '0.72rem',
                  padding: '0.25rem 0.65rem',
                  borderRadius: '6px',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Frequency Selector */}
          <select value={frequency} onChange={(e) => setFrequency(e.target.value as any)}>
            <option value="DAILY">Daily Rebalance</option>
            <option value="WEEKLY">Weekly Rebalance</option>
            <option value="MONTHLY">Monthly Rebalance</option>
          </select>

          {/* Run Button */}
          <button
            onClick={executeBacktest}
            disabled={loading}
            className="btn btn-primary"
            style={{ padding: '0.45rem 0.85rem' }}
          >
            <RotateCw size={13} className={loading ? 'animate-spin' : ''} />
            <span>{loading ? 'Simulating...' : 'Run Backtest'}</span>
          </button>

        </div>
      </div>

      {error && (
        <div style={{ padding: '0.75rem', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', borderRadius: '8px', color: '#FB7185', fontSize: '0.78rem' }}>
          {error}
        </div>
      )}

      {/* KPI Comparative Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: '0.75rem'
      }}>
        
        {/* Cumulative Return */}
        <div style={{ background: 'var(--bg-input)', padding: '0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Cumulative Return</div>
          <div className="font-mono" style={{
            fontSize: '1.2rem',
            fontWeight: 800,
            marginTop: '0.25rem',
            color: nlp && nlp.cumulative_return_pct >= 0 ? '#34D399' : '#FB7185'
          }}>
            NLP: {nlp ? `${nlp.cumulative_return_pct >= 0 ? '+' : ''}${nlp.cumulative_return_pct.toFixed(2)}%` : '--'}
          </div>
          <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>
            Base: {baseline ? `${baseline.cumulative_return_pct >= 0 ? '+' : ''}${baseline.cumulative_return_pct.toFixed(2)}%` : '--'}
          </div>
        </div>

        {/* Active Alpha */}
        <div style={{ background: 'var(--bg-input)', padding: '0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Active Alpha</div>
          <div className="font-mono" style={{
            fontSize: '1.2rem',
            fontWeight: 800,
            marginTop: '0.25rem',
            color: backtestResult && backtestResult.outperformance_pct >= 0 ? '#34D399' : '#FB7185'
          }}>
            {backtestResult ? `${backtestResult.outperformance_pct >= 0 ? '+' : ''}${backtestResult.outperformance_pct.toFixed(2)}%` : '--'}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>Net of 10 bps fees</div>
        </div>

        {/* Volatility */}
        <div style={{ background: 'var(--bg-input)', padding: '0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Volatility</div>
          <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
            {nlp ? `${nlp.annualized_volatility_pct.toFixed(2)}%` : '--'}
          </div>
          <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>
            Base: {baseline ? `${baseline.annualized_volatility_pct.toFixed(2)}%` : '--'}
          </div>
        </div>

        {/* Drawdown */}
        <div style={{ background: 'var(--bg-input)', padding: '0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Max Drawdown</div>
          <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: '#FB7185', marginTop: '0.25rem' }}>
            {nlp ? `-${nlp.max_drawdown_pct.toFixed(2)}%` : '--'}
          </div>
          <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>
            Base: {baseline ? `-${baseline.max_drawdown_pct.toFixed(2)}%` : '--'}
          </div>
        </div>

        {/* Sharpe */}
        <div style={{ background: 'var(--bg-input)', padding: '0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Sharpe Ratio</div>
          <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--color-cyan)', marginTop: '0.25rem' }}>
            {nlp ? nlp.sharpe_ratio.toFixed(2) : '--'}
          </div>
          <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>
            Base: {baseline ? baseline.sharpe_ratio.toFixed(2) : '--'}
          </div>
        </div>

        {/* Turnover */}
        <div style={{ background: 'var(--bg-input)', padding: '0.85rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Total Turnover</div>
          <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--color-indigo)', marginTop: '0.25rem' }}>
            {nlp ? `${nlp.total_turnover_pct.toFixed(2)}%` : '--'}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>
            Win Rate: {nlp ? `${nlp.win_rate_pct.toFixed(0)}%` : '--'}
          </div>
        </div>

      </div>

      {/* Equity Curve SVG Chart */}
      <div style={{
        background: 'var(--bg-input)',
        padding: '1.25rem',
        borderRadius: '12px',
        border: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem'
      }}>
        
        {/* Chart Legend */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.75rem',
          paddingBottom: '0.5rem',
          borderBottom: '1px solid var(--border-subtle)',
          gap: '1rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span style={{ width: '12px', height: '2px', background: 'var(--text-tertiary)' }} />
              <span style={{ color: 'var(--text-secondary)' }}>Baseline Equal-Weight Index</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span style={{ width: '12px', height: '3px', background: '#34D399', borderRadius: '2px' }} />
              <span style={{ color: '#34D399', fontWeight: 700 }}>NLP Tactical Strategy</span>
            </div>
          </div>

          <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>
            {backtestResult?.total_periods || 0} Periods Simulated &bull; Y-Axis: Cumulative Return %
          </div>
        </div>

        {/* SVG Equity Lines */}
        <div style={{ position: 'relative', width: '100%', height: '200px' }}>
          {trajectory.length < 2 ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
              {loading ? 'Simulating historical equity trajectories...' : 'Run a backtest to view historical performance.'}
            </div>
          ) : (
            <div style={{ width: '100%', height: '100%', position: 'relative' }}>
              
              {/* Zero return line */}
              <div style={{
                position: 'absolute',
                left: 0,
                right: 0,
                top: `${((maxVal - 0) / range) * 100}%`,
                borderBottom: '1px dashed var(--border-medium)',
                pointerEvents: 'none'
              }}>
                <span className="font-mono" style={{ position: 'absolute', left: 0, top: '-14px', fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
                  0.0%
                </span>
              </div>

              <svg viewBox="0 0 800 180" preserveAspectRatio="none" style={{ width: '100%', height: '160px', overflow: 'visible' }}>
                
                {/* Baseline Line */}
                <path
                  d={generatePath('baseline_cumulative_return_pct')}
                  fill="none"
                  stroke="#64748B"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                />

                {/* NLP Strategy Line */}
                <path
                  d={generatePath('nlp_cumulative_return_pct')}
                  fill="none"
                  stroke="#34D399"
                  strokeWidth="3"
                />

                {/* Circles for points */}
                {trajectory.map((p, idx) => {
                  const width = 800;
                  const height = 180;
                  const stepX = width / (trajectory.length - 1);
                  const x = idx * stepX;
                  const yNlp = height - ((p.nlp_cumulative_return_pct - minVal) / range) * height;

                  return (
                    <circle
                      key={idx}
                      cx={x}
                      cy={yNlp}
                      r="4"
                      fill="#34D399"
                      stroke="#070B14"
                      strokeWidth="2"
                    >
                      <title>{`Period ${p.period_index} (${p.date}): NLP ${p.nlp_cumulative_return_pct.toFixed(2)}% vs Base ${p.baseline_cumulative_return_pct.toFixed(2)}%`}</title>
                    </circle>
                  );
                })}

              </svg>

              {/* Date Labels */}
              <div className="font-mono" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.35rem' }}>
                <span>{trajectory[0]?.rebalance_date}</span>
                <span>{trajectory[Math.floor(trajectory.length / 2)]?.date}</span>
                <span>{trajectory[trajectory.length - 1]?.date}</span>
              </div>

            </div>
          )}
        </div>

      </div>

      {/* Assumptions & Disclosures */}
      <div style={{
        background: 'var(--bg-input)',
        padding: '1rem',
        borderRadius: '10px',
        border: '1px solid var(--border-subtle)',
        fontSize: '0.75rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.4rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontWeight: 700, color: 'var(--text-primary)' }}>
          <Info size={14} style={{ color: 'var(--color-cyan)' }} />
          <span>Research & Demo Backtest Disclosures (Module A):</span>
        </div>
        <ul style={{ color: 'var(--text-secondary)', paddingLeft: '1.25rem', lineHeight: 1.6 }}>
          {backtestResult?.assumptions && typeof backtestResult.assumptions === 'object' && !Array.isArray(backtestResult.assumptions) ? (
            Object.entries(backtestResult.assumptions).map(([key, val]) => (
              <li key={key}>
                <strong style={{ color: '#FFFFFF', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}:</strong> {String(val)}
              </li>
            ))
          ) : Array.isArray(backtestResult?.assumptions) ? (
            backtestResult.assumptions.map((ass, i) => (
              <li key={`ass-${i}`}>{ass}</li>
            ))
          ) : (
            <>
              <li>Baseline index is an equal-weighted 15-stock mock index rebalanced to 6.67% baseline.</li>
              <li>Signals are evaluated with zero look-ahead bias: strictly before the rebalancing timestamp.</li>
              <li>Realistic execution slippage and transaction costs deducted at 10 bps (0.10%) per trade.</li>
            </>
          )}
          {backtestResult?.disclaimer && (
            <li style={{ color: '#FBBF24', fontWeight: 600 }}>{backtestResult.disclaimer}</li>
          )}
        </ul>
      </div>

    </div>
  );
};
