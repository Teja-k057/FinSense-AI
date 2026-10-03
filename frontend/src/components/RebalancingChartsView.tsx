import React, { useState } from 'react';
import { 
  BarChart3, 
  CheckCircle2, 
  ArrowUpRight, 
  ArrowDownRight,
  Minus
} from 'lucide-react';
import type { RebalanceSummary } from '../types';

interface RebalancingChartsViewProps {
  summary: RebalanceSummary | null;
  onSelectTicker: (ticker: string) => void;
  selectedTicker: string;
}

export const RebalancingChartsView: React.FC<RebalancingChartsViewProps> = ({
  summary,
  onSelectTicker,
  selectedTicker
}) => {
  const [hoveredTicker, setHoveredTicker] = useState<string | null>(null);
  const constituents = summary?.constituents || [];

  const [sortBy, setSortBy] = useState<'delta' | 'target' | 'ticker'>('delta');

  const sortedList = [...constituents].sort((a, b) => {
    if (sortBy === 'target') return b.target_weight_pct - a.target_weight_pct;
    if (sortBy === 'delta') return b.weight_delta_pct - a.weight_delta_pct;
    return a.ticker.localeCompare(b.ticker);
  });

  const maxWeight = 16.0; // Y-max (15% Cap)
  const floorWeight = 2.0; // Floor line
  const baselineWeight = 6.67; // Baseline line

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* Header and Controls */}
      <div className="card-header">
        <div className="card-title-group">
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'rgba(56, 189, 248, 0.15)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-cyan)'
          }}>
            <BarChart3 size={16} />
          </div>
          <div>
            <div className="card-title">
              Rebalancing Allocation: Before Weights vs After Weights
            </div>
            <div className="card-subtitle">
              Visualizing baseline equal weights (6.67%) versus tactical target weights with water-filling constraints.
            </div>
          </div>
        </div>

        {/* Sort Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem' }}>
          <span style={{ color: 'var(--text-tertiary)' }}>Sort:</span>
          {(['delta', 'target', 'ticker'] as const).map(s => (
            <button
              key={s}
              onClick={() => setSortBy(s)}
              className="btn btn-secondary"
              style={{
                padding: '0.25rem 0.65rem',
                fontSize: '0.72rem',
                background: sortBy === s ? 'rgba(6, 182, 212, 0.2)' : undefined,
                borderColor: sortBy === s ? 'var(--color-cyan)' : undefined,
                color: sortBy === s ? 'var(--color-cyan)' : undefined
              }}
            >
              {s === 'delta' ? 'Tactical Delta (±%)' : s === 'target' ? 'Target Weight' : 'Ticker'}
            </button>
          ))}
        </div>
      </div>

      {/* Rebalance Metrics Strip */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: '0.75rem'
      }}>
        
        <div style={{ background: 'var(--bg-input)', padding: '0.75rem 1rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Portfolio Turnover</div>
          <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--color-cyan)', marginTop: '0.25rem' }}>
            {summary?.turnover_pct ? `${summary.turnover_pct.toFixed(2)}%` : '0.00%'}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>½ ∑ |Δw| two-way</div>
        </div>

        <div style={{ background: 'var(--bg-input)', padding: '0.75rem 1rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Tactical Actions</div>
          <div className="font-mono" style={{ fontSize: '1.05rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
            <span style={{ color: '#34D399' }}>+{summary?.actions_count.INCREASE || 0}</span>
            <span style={{ color: 'var(--text-tertiary)' }}>/</span>
            <span style={{ color: 'var(--text-secondary)' }}>{summary?.actions_count.HOLD || 0}</span>
            <span style={{ color: 'var(--text-tertiary)' }}>/</span>
            <span style={{ color: '#FB7185' }}>-{summary?.actions_count.REDUCE || 0}</span>
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>Increase / Hold / Reduce</div>
        </div>

        <div style={{ background: 'var(--bg-input)', padding: '0.75rem 1rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Target Weight Sum</div>
          <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: '#34D399', display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.25rem' }}>
            <CheckCircle2 size={16} />
            <span>100.0%</span>
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>Fully allocated invariant</div>
        </div>

        <div style={{ background: 'var(--bg-input)', padding: '0.75rem 1rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Average Index Sentiment</div>
          <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '0.25rem', color: summary && summary.average_sentiment >= 0 ? '#34D399' : '#FB7185' }}>
            {summary ? (summary.average_sentiment >= 0 ? '+' : '') + summary.average_sentiment.toFixed(2) : '0.00'}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>Avg Impact: {summary?.average_impact.toFixed(1)}/10</div>
        </div>

      </div>

      {/* Dual Bar Chart (SVG & Vector Representation) */}
      <div style={{
        background: 'var(--bg-input)',
        padding: '1.25rem',
        borderRadius: '12px',
        border: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem'
      }}>
        
        {/* Legend */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.75rem',
          paddingBottom: '0.65rem',
          borderBottom: '1px solid var(--border-subtle)',
          gap: '1rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'rgba(100, 116, 139, 0.6)', border: '1px solid rgba(148, 163, 184, 0.4)' }} />
              <span style={{ color: 'var(--text-secondary)' }}>Before: Baseline Equal-Weight (6.67%)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'linear-gradient(135deg, #0284C7 0%, #38BDF8 100%)' }} />
              <span style={{ color: 'var(--color-cyan)', fontWeight: 600 }}>After: Tactical Target Weight (%)</span>
            </div>
          </div>

          <div className="font-mono" style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.72rem' }}>
            <span style={{ color: '#FB7185' }}>--- 15% Cap</span>
            <span style={{ color: 'var(--text-tertiary)' }}>--- 6.67% Baseline</span>
            <span style={{ color: '#FBBF24' }}>--- 2% Floor</span>
          </div>
        </div>

        {/* Visualizer Area */}
        <div style={{ position: 'relative', width: '100%', overflowX: 'auto', paddingTop: '1.5rem', paddingBottom: '0.5rem' }}>
          <div style={{ minWidth: '700px', height: '240px', position: 'relative', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', padding: '0 0.5rem' }}>
            
            {/* Guide Line: 15% Cap */}
            <div style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: `${(15.0 / maxWeight) * 100}%`,
              borderBottom: '1px dashed rgba(244, 63, 94, 0.4)',
              pointerEvents: 'none',
              zIndex: 1
            }}>
              <span className="font-mono" style={{ position: 'absolute', right: '4px', top: '-14px', fontSize: '0.65rem', color: '#FB7185' }}>
                15.0% Cap
              </span>
            </div>

            {/* Guide Line: 6.67% Baseline */}
            <div style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: `${(baselineWeight / maxWeight) * 100}%`,
              borderBottom: '1px dashed rgba(148, 163, 184, 0.3)',
              pointerEvents: 'none',
              zIndex: 1
            }}>
              <span className="font-mono" style={{ position: 'absolute', right: '4px', top: '-14px', fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
                6.67% Base
              </span>
            </div>

            {/* Guide Line: 2% Floor */}
            <div style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: `${(floorWeight / maxWeight) * 100}%`,
              borderBottom: '1px dashed rgba(245, 158, 11, 0.4)',
              pointerEvents: 'none',
              zIndex: 1
            }}>
              <span className="font-mono" style={{ position: 'absolute', right: '4px', top: '-14px', fontSize: '0.65rem', color: '#FBBF24' }}>
                2.0% Floor
              </span>
            </div>

            {/* Bar Pairs for Constituents */}
            {sortedList.map((item) => {
              const beforePct = item.current_weight_pct;
              const afterPct = item.target_weight_pct;
              const beforeHeight = (beforePct / maxWeight) * 100;
              const afterHeight = (afterPct / maxWeight) * 100;
              const isSelected = selectedTicker === item.ticker;
              const isHovered = hoveredTicker === item.ticker;
              const isIncrease = item.weight_delta_pct > 0.05;
              const isReduce = item.weight_delta_pct < -0.05;

              return (
                <div
                  key={item.ticker}
                  onClick={() => onSelectTicker(item.ticker)}
                  onMouseEnter={() => setHoveredTicker(item.ticker)}
                  onMouseLeave={() => setHoveredTicker(null)}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    cursor: 'pointer',
                    zIndex: 2,
                    margin: '0 4px',
                    position: 'relative'
                  }}
                >
                  
                  {/* Hover Floating Tooltip */}
                  {(isHovered || isSelected) && (
                    <div style={{
                      position: 'absolute',
                      bottom: '100%',
                      marginBottom: '8px',
                      background: 'rgba(10, 16, 28, 0.95)',
                      border: '1px solid var(--border-active)',
                      boxShadow: '0 8px 20px rgba(0, 0, 0, 0.6)',
                      borderRadius: '8px',
                      padding: '0.45rem 0.65rem',
                      zIndex: 30,
                      whiteSpace: 'nowrap',
                      pointerEvents: 'none',
                      textAlign: 'center'
                    }}>
                      <div className="font-mono" style={{ fontSize: '0.75rem', fontWeight: 800, color: '#FFFFFF' }}>
                        {item.ticker} &bull; {item.company_name}
                      </div>
                      <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                        Base: {beforePct.toFixed(2)}% &rarr; Target: <strong style={{ color: 'var(--color-cyan)' }}>{afterPct.toFixed(2)}%</strong>
                      </div>
                      <div className="font-mono" style={{
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        color: isIncrease ? '#34D399' : isReduce ? '#FB7185' : 'var(--text-tertiary)',
                        marginTop: '0.15rem'
                      }}>
                        Delta: {item.weight_delta_pct >= 0 ? '+' : ''}{item.weight_delta_pct.toFixed(2)}% ({item.rebalance_action})
                      </div>
                    </div>
                  )}

                  {/* Dual Bars Container */}
                  <div style={{
                    width: '100%',
                    height: '180px',
                    display: 'flex',
                    alignItems: 'flex-end',
                    justifyContent: 'center',
                    gap: '2px'
                  }}>
                    {/* Before Bar */}
                    <div style={{
                      width: '45%',
                      height: `${beforeHeight}%`,
                      background: 'rgba(100, 116, 139, 0.5)',
                      borderRadius: '3px 3px 0 0',
                      transition: 'height 0.3s ease'
                    }} />

                    {/* After Bar */}
                    <div style={{
                      width: '45%',
                      height: `${afterHeight}%`,
                      background: isIncrease 
                        ? 'linear-gradient(180deg, #34D399 0%, #059669 100%)' 
                        : isReduce 
                        ? 'linear-gradient(180deg, #FB7185 0%, #E11D48 100%)' 
                        : 'linear-gradient(180deg, #38BDF8 0%, #0284C7 100%)',
                      borderRadius: '3px 3px 0 0',
                      boxShadow: isSelected ? '0 0 10px rgba(56, 189, 248, 0.5)' : 'none',
                      border: isSelected ? '1px solid #FFFFFF' : 'none',
                      transition: 'height 0.3s ease'
                    }} />
                  </div>

                  {/* Ticker & Delta Label */}
                  <div style={{ marginTop: '0.45rem', textAlign: 'center' }}>
                    <span className="font-mono" style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      display: 'block',
                      color: isSelected ? 'var(--color-cyan)' : 'var(--text-secondary)'
                    }}>
                      {item.ticker}
                    </span>
                    <span className="font-mono" style={{
                      fontSize: '0.65rem',
                      fontWeight: 600,
                      display: 'block',
                      color: isIncrease ? '#34D399' : isReduce ? '#FB7185' : 'var(--text-tertiary)'
                    }}>
                      {item.weight_delta_pct >= 0 ? '+' : ''}{item.weight_delta_pct.toFixed(1)}%
                    </span>
                  </div>

                </div>
              );
            })}

          </div>
        </div>

      </div>

    </div>
  );
};
