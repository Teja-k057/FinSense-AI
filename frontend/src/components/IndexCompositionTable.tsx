import React, { useState } from 'react';
import { 
  ArrowUpRight, 
  ArrowDownRight, 
  Minus, 
  Layers, 
  ChevronRight,
  Info
} from 'lucide-react';
import type { ConstituentRebalanceDetail, RebalanceAction } from '../types';

interface IndexCompositionTableProps {
  constituents: ConstituentRebalanceDetail[];
  selectedTicker: string;
  onSelectTicker: (ticker: string) => void;
}

export const IndexCompositionTable: React.FC<IndexCompositionTableProps> = ({
  constituents,
  selectedTicker,
  onSelectTicker
}) => {
  const [sortField, setSortField] = useState<'ticker' | 'current' | 'target' | 'delta'>('delta');
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort = (field: 'ticker' | 'current' | 'target' | 'delta') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const sortedConstituents = [...constituents].sort((a, b) => {
    let comparison = 0;
    if (sortField === 'ticker') comparison = a.ticker.localeCompare(b.ticker);
    else if (sortField === 'current') comparison = a.current_weight_pct - b.current_weight_pct;
    else if (sortField === 'target') comparison = a.target_weight_pct - b.target_weight_pct;
    else if (sortField === 'delta') comparison = a.weight_delta_pct - b.weight_delta_pct;
    return sortAsc ? comparison : -comparison;
  });

  const getActionBadge = (action: RebalanceAction) => {
    switch (action) {
      case 'INCREASE':
        return <span className="badge badge-emerald"><ArrowUpRight size={11} /> INCREASE</span>;
      case 'REDUCE':
        return <span className="badge badge-rose"><ArrowDownRight size={11} /> REDUCE</span>;
      case 'HOLD':
      default:
        return <span className="badge badge-slate"><Minus size={11} /> HOLD</span>;
    }
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      
      {/* Header */}
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
            <Layers size={16} />
          </div>
          <div>
            <div className="card-title">
              Index Constituents & Weight Allocations (15 Liquid Equities)
            </div>
            <div className="card-subtitle">
              Live yfinance market quotes and sentiment-adjusted targets. Click any stock to view its deep-dive and signal attribution.
            </div>
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', fontSize: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#34D399' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#34D399' }} />
            <span>Increase</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-tertiary)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--text-tertiary)' }} />
            <span>Hold</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#FB7185' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#FB7185' }} />
            <span>Reduce</span>
          </div>
        </div>
      </div>

      {/* Table View */}
      <div className="table-responsive">
        <table>
          <thead>
            <tr>
              <th onClick={() => handleSort('ticker')} style={{ cursor: 'pointer' }}>
                Ticker {sortField === 'ticker' && (sortAsc ? '▲' : '▼')}
              </th>
              <th>Company Name</th>
              <th>Sector</th>
              <th>Market Price</th>
              <th onClick={() => handleSort('current')} style={{ cursor: 'pointer' }}>
                Current Weight {sortField === 'current' && (sortAsc ? '▲' : '▼')}
              </th>
              <th onClick={() => handleSort('target')} style={{ cursor: 'pointer' }}>
                Target Weight {sortField === 'target' && (sortAsc ? '▲' : '▼')}
              </th>
              <th onClick={() => handleSort('delta')} style={{ cursor: 'pointer' }}>
                Weight Change {sortField === 'delta' && (sortAsc ? '▲' : '▼')}
              </th>
              <th>Tactical Action</th>
              <th>Sentiment & Event</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sortedConstituents.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-tertiary)' }}>
                  Loading constituents...
                </td>
              </tr>
            ) : (
              sortedConstituents.map((item) => {
                const isSelected = selectedTicker === item.ticker;
                const isPositiveDelta = item.weight_delta_pct > 0.01;
                const isNegativeDelta = item.weight_delta_pct < -0.01;

                return (
                  <tr
                    key={item.ticker}
                    onClick={() => onSelectTicker(item.ticker)}
                    className={isSelected ? 'selected-row' : ''}
                    style={{ cursor: 'pointer' }}
                  >
                    
                    {/* Ticker */}
                    <td className="font-mono" style={{ fontWeight: 800 }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '6px',
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-medium)',
                        color: 'var(--color-cyan)',
                        fontSize: '0.8rem'
                      }}>
                        {item.ticker}
                      </span>
                    </td>

                    {/* Company Name */}
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.company_name}
                    </td>

                    {/* Sector */}
                    <td style={{ color: 'var(--text-secondary)' }}>
                      {item.sector}
                    </td>

                    {/* Current Price */}
                    <td className="font-mono">
                      <div>${item.current_price.toFixed(2)}</div>
                      <div style={{
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        color: item.recent_return >= 0 ? '#34D399' : '#FB7185'
                      }}>
                        {item.recent_return >= 0 ? '+' : ''}{(item.recent_return * 100).toFixed(2)}%
                      </div>
                    </td>

                    {/* Current Weight */}
                    <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {item.current_weight_pct.toFixed(2)}%
                    </td>

                    {/* Target Weight */}
                    <td className="font-mono" style={{ fontWeight: 800, color: '#FFFFFF' }}>
                      {item.target_weight_pct.toFixed(2)}%
                    </td>

                    {/* Weight Change */}
                    <td className="font-mono" style={{ fontWeight: 700 }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '0.2rem 0.55rem',
                        borderRadius: '6px',
                        fontSize: '0.78rem',
                        color: isPositiveDelta ? '#34D399' : isNegativeDelta ? '#FB7185' : 'var(--text-secondary)',
                        background: isPositiveDelta ? 'rgba(16, 185, 129, 0.12)' : isNegativeDelta ? 'rgba(244, 63, 94, 0.12)' : 'rgba(100, 116, 139, 0.12)',
                        border: isPositiveDelta ? '1px solid rgba(16, 185, 129, 0.3)' : isNegativeDelta ? '1px solid rgba(244, 63, 94, 0.3)' : '1px solid rgba(100, 116, 139, 0.2)'
                      }}>
                        {isPositiveDelta ? '+' : ''}{item.weight_delta_pct.toFixed(2)}%
                      </span>
                    </td>

                    {/* Action */}
                    <td>
                      {getActionBadge(item.rebalance_action)}
                    </td>

                    {/* Sentiment & Event */}
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                        <span className="font-mono" style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          color: item.latest_sentiment_score > 0.05 ? '#34D399' : item.latest_sentiment_score < -0.05 ? '#FB7185' : 'var(--text-tertiary)'
                        }}>
                          {item.latest_sentiment_score >= 0 ? '+' : ''}{item.latest_sentiment_score.toFixed(2)}
                        </span>
                        <span style={{ color: 'var(--text-tertiary)' }}>&bull;</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {item.latest_event_type}
                        </span>
                      </div>
                    </td>

                    {/* Inspect link */}
                    <td style={{ textAlign: 'right' }}>
                      <ChevronRight size={16} style={{ color: isSelected ? 'var(--color-cyan)' : 'var(--text-tertiary)' }} />
                    </td>

                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Constraints Notice footer */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '0.75rem',
        color: 'var(--text-tertiary)',
        paddingTop: '0.5rem',
        borderTop: '1px solid var(--border-subtle)',
        gap: '0.75rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Info size={14} style={{ color: 'var(--color-cyan)' }} />
          <span>Water-filling allocation constraints applied: <strong>2.0% floor</strong> &le; weight &le; <strong>15.0% cap</strong>. Sum = 100.0%.</span>
        </div>
        <div className="font-mono" style={{ color: 'var(--color-cyan)', fontWeight: 700 }}>
          Total Target Weight: {constituents.reduce((sum, c) => sum + c.target_weight_pct, 0).toFixed(1)}%
        </div>
      </div>

    </div>
  );
};
