import React from 'react';
import { 
  Building2, 
  TrendingUp, 
  TrendingDown, 
  Sparkles, 
  FileText, 
  ExternalLink 
} from 'lucide-react';
import type { ConstituentRebalanceDetail, RiskSignalItem, NewsArticleItem } from '../types';
import { SignalExplanationCard } from './SignalExplanationCard';

interface StockDetailSectionProps {
  selectedTicker: string;
  onSelectTicker: (ticker: string) => void;
  constituents: ConstituentRebalanceDetail[];
  signals: RiskSignalItem[];
  newsArticles: NewsArticleItem[];
}

export const StockDetailSection: React.FC<StockDetailSectionProps> = ({
  selectedTicker,
  onSelectTicker,
  constituents,
  signals,
  newsArticles
}) => {
  const constituent = constituents.find(c => c.ticker === selectedTicker) || constituents[0] || null;

  const companySignals = signals.filter(s => s.company === constituent?.ticker);
  const companyNews = newsArticles.filter(n => 
    n.company_entities?.includes(constituent?.ticker || '') ||
    n.title.toLowerCase().includes(constituent?.ticker.toLowerCase() || '') ||
    (constituent?.company_name && n.title.toLowerCase().includes(constituent.company_name.toLowerCase()))
  );

  if (!constituent) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-tertiary)' }}>
        No constituent selected.
      </div>
    );
  }

  const isPositiveReturn = constituent.recent_return >= 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* Stock Selection Bar & Metrics Ribbon */}
      <div className="card">
        
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingBottom: '1rem',
          borderBottom: '1px solid var(--border-subtle)',
          gap: '1rem'
        }}>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <div className="font-mono" style={{
              width: '46px',
              height: '46px',
              borderRadius: '12px',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-active)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.1rem',
              fontWeight: 800,
              color: 'var(--color-cyan)',
              boxShadow: '0 4px 15px rgba(6, 182, 212, 0.15)'
            }}>
              {constituent.ticker}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
                  {constituent.company_name}
                </h3>
                <span className="badge badge-slate" style={{ fontSize: '0.68rem' }}>
                  {constituent.sector}
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                S&P Global × CRISIL Tactical Index Constituent
              </div>
            </div>
          </div>

          {/* Stock Switcher Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Select Stock:</span>
            <select
              value={constituent.ticker}
              onChange={(e) => onSelectTicker(e.target.value)}
              className="font-mono"
              style={{ fontWeight: 700, color: 'var(--color-cyan)', padding: '0.45rem 0.85rem' }}
            >
              {constituents.map(c => (
                <option key={c.ticker} value={c.ticker}>
                  {c.ticker} &bull; {c.company_name} ({c.rebalance_action})
                </option>
              ))}
            </select>
          </div>

        </div>

        {/* Financial Metrics Strip */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '0.75rem',
          marginTop: '1rem'
        }}>
          
          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Market Price</span>
            <div className="font-mono" style={{ fontSize: '1.15rem', fontWeight: 800, color: '#FFFFFF', marginTop: '0.2rem' }}>
              ${constituent.current_price.toFixed(2)}
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>yfinance live</span>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>1-Day Return</span>
            <div className="font-mono" style={{
              fontSize: '1.15rem',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              marginTop: '0.2rem',
              color: isPositiveReturn ? '#34D399' : '#FB7185'
            }}>
              {isPositiveReturn ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
              <span>{isPositiveReturn ? '+' : ''}{(constituent.recent_return * 100).toFixed(2)}%</span>
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>Momentum factor</span>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Volatility</span>
            <div className="font-mono" style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
              {constituent.volatility ? `${(constituent.volatility * 100).toFixed(1)}%` : '18.5%'}
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>1-Month Ann.</span>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Current Weight</span>
            <div className="font-mono" style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              {constituent.current_weight_pct.toFixed(2)}%
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>Baseline equal-weight</span>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Target Weight</span>
            <div className="font-mono" style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--color-cyan)', marginTop: '0.2rem' }}>
              {constituent.target_weight_pct.toFixed(2)}%
            </div>
            <span className="font-mono" style={{
              fontSize: '0.68rem',
              fontWeight: 700,
              color: constituent.weight_delta_pct >= 0 ? '#34D399' : '#FB7185'
            }}>
              Δ {constituent.weight_delta_pct >= 0 ? '+' : ''}{constituent.weight_delta_pct.toFixed(2)}%
            </span>
          </div>

        </div>

      </div>

      {/* Signal Explanation Section */}
      <SignalExplanationCard constituent={constituent} />

      {/* Side-by-side Intelligence Grid */}
      <div className="split-view">
        
        {/* Left: Signals for this stock */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <div className="card-header" style={{ margin: 0 }}>
            <div className="card-title-group">
              <Sparkles size={16} style={{ color: 'var(--color-indigo)' }} />
              <div>
                <div className="card-title" style={{ fontSize: '0.85rem' }}>
                  Risk Engine Signals ({companySignals.length})
                </div>
                <div className="card-subtitle">Constituent: {constituent.ticker}</div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', maxHeight: '350px', overflowY: 'auto' }}>
            {companySignals.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.78rem' }}>
                No recent signals detected for {constituent.ticker}. Using neutral baseline allocation.
              </div>
            ) : (
              companySignals.map((sig, idx) => (
                <div key={sig.id || idx} style={{
                  background: 'var(--bg-input)',
                  padding: '0.85rem',
                  borderRadius: '10px',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.4rem',
                  fontSize: '0.78rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifySelf: 'space-between', justifyContent: 'space-between' }}>
                    <span style={{
                      padding: '0.15rem 0.5rem',
                      borderRadius: '4px',
                      background: 'var(--bg-surface-elevated)',
                      color: 'var(--color-cyan)',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      border: '1px solid var(--border-medium)'
                    }}>
                      {sig.event_type}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className="font-mono" style={{
                        fontWeight: 700,
                        color: sig.sentiment_score > 0.05 ? '#34D399' : sig.sentiment_score < -0.05 ? '#FB7185' : 'var(--text-tertiary)'
                      }}>
                        Sentiment: {sig.sentiment_score >= 0 ? '+' : ''}{sig.sentiment_score.toFixed(2)}
                      </span>
                      <span className="badge badge-amber" style={{ fontSize: '0.65rem' }}>
                        Impact: {sig.impact_score.toFixed(1)}/10
                      </span>
                    </div>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                    {sig.explanation}
                  </p>
                  <div className="font-mono" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-tertiary)', paddingTop: '0.25rem' }}>
                    <span>Source: {sig.source}</span>
                    <span>{new Date(sig.timestamp).toLocaleDateString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Associated News Articles */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <div className="card-header" style={{ margin: 0 }}>
            <div className="card-title-group">
              <FileText size={16} style={{ color: 'var(--color-cyan)' }} />
              <div>
                <div className="card-title" style={{ fontSize: '0.85rem' }}>
                  Related Financial News ({companyNews.length})
                </div>
                <div className="card-subtitle">Ingested Feed Attribution</div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', maxHeight: '350px', overflowY: 'auto' }}>
            {companyNews.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.78rem' }}>
                No specific news articles mapped for {constituent.ticker}. Ingest live articles using the top ribbon.
              </div>
            ) : (
              companyNews.map((art, idx) => (
                <div key={art.id || idx} style={{
                  background: 'var(--bg-input)',
                  padding: '0.85rem',
                  borderRadius: '10px',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.35rem',
                  fontSize: '0.78rem'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 700, color: '#FFFFFF', lineHeight: 1.3 }}>{art.title}</span>
                    <span className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
                      {art.source}
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.74rem', lineHeight: 1.4 }}>
                    {art.text.substring(0, 140)}...
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.68rem', color: 'var(--text-tertiary)', paddingTop: '0.25rem' }}>
                    <span>{new Date(art.publication_time).toLocaleDateString()}</span>
                    {art.url && (
                      <a 
                        href={art.url} 
                        target="_blank" 
                        rel="noreferrer" 
                        style={{ color: 'var(--color-cyan)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                      >
                        <span>Article Link</span>
                        <ExternalLink size={11} />
                      </a>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
};
