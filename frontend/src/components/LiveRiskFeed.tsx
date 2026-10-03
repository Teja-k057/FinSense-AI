import React, { useState, useMemo } from 'react';
import { 
  Radio, 
  Search, 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  ChevronRight 
} from 'lucide-react';
import type { RiskSignalItem, RiskLevel } from '../types';

interface LiveRiskFeedProps {
  signals: RiskSignalItem[];
  onSelectCompany: (ticker: string) => void;
  selectedCompany?: string;
}

export const LiveRiskFeed: React.FC<LiveRiskFeedProps> = ({
  signals,
  onSelectCompany,
  selectedCompany
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<string>('ALL');
  const [selectedSentiment, setSelectedSentiment] = useState<string>('ALL');
  const [minImpact, setMinImpact] = useState<number>(1.0);
  const [sourceFilter, setSourceFilter] = useState<string>('ALL');

  const eventTypes = useMemo(() => {
    const set = new Set<string>();
    signals.forEach(s => {
      if (s.event_type) set.add(s.event_type);
    });
    return Array.from(set).sort();
  }, [signals]);

  const filteredSignals = useMemo(() => {
    return signals.filter(sig => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesTicker = sig.company?.toLowerCase().includes(q);
        const matchesExpl = sig.explanation?.toLowerCase().includes(q);
        const matchesEvent = sig.event_type?.toLowerCase().includes(q);
        if (!matchesTicker && !matchesExpl && !matchesEvent) return false;
      }
      if (selectedEvent !== 'ALL' && sig.event_type !== selectedEvent) return false;
      if (selectedSentiment === 'POSITIVE' && sig.sentiment_score <= 0.05) return false;
      if (selectedSentiment === 'NEGATIVE' && sig.sentiment_score >= -0.05) return false;
      if (selectedSentiment === 'NEUTRAL' && (sig.sentiment_score > 0.05 || sig.sentiment_score < -0.05)) return false;
      if (sig.impact_score < minImpact) return false;
      if (sourceFilter !== 'ALL' && !sig.source?.toLowerCase().includes(sourceFilter.toLowerCase())) return false;
      return true;
    });
  }, [signals, searchQuery, selectedEvent, selectedSentiment, minImpact, sourceFilter]);

  const getRiskBadge = (level: RiskLevel) => {
    switch (level) {
      case 'CRITICAL': return <span className="badge badge-rose">CRITICAL</span>;
      case 'HIGH': return <span className="badge badge-amber">HIGH</span>;
      case 'MEDIUM': return <span className="badge badge-cyan">MEDIUM</span>;
      default: return <span className="badge badge-slate">LOW</span>;
    }
  };

  const getSentimentPill = (score: number) => {
    if (score > 0.05) {
      return (
        <span className="font-mono" style={{ color: '#34D399', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
          <TrendingUp size={13} />
          +{score.toFixed(2)}
        </span>
      );
    }
    if (score < -0.05) {
      return (
        <span className="font-mono" style={{ color: '#FB7185', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
          <TrendingDown size={13} />
          {score.toFixed(2)}
        </span>
      );
    }
    return (
      <span className="font-mono" style={{ color: 'var(--text-tertiary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
        <Minus size={13} />
        0.00
      </span>
    );
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      
      {/* Header and Filter Bar */}
      <div className="card-header">
        <div className="card-title-group">
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'rgba(99, 102, 241, 0.15)',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-indigo)'
          }}>
            <Radio size={16} />
          </div>
          <div>
            <div className="card-title">Live AI/NLP Risk Intelligence Feed</div>
            <div className="card-subtitle">
              Continuous canonical signals processed across GDELT live news and Kaggle Financial PhraseBank.
            </div>
          </div>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
          
          {/* Search Box */}
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              placeholder="Search ticker, event..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '1.75rem', width: '160px' }}
            />
            <Search size={12} style={{ position: 'absolute', left: '0.6rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)' }} />
          </div>

          {/* Event Filter */}
          <select value={selectedEvent} onChange={(e) => setSelectedEvent(e.target.value)}>
            <option value="ALL">All Event Types</option>
            {eventTypes.map(ev => <option key={ev} value={ev}>{ev}</option>)}
          </select>

          {/* Sentiment Filter */}
          <select value={selectedSentiment} onChange={(e) => setSelectedSentiment(e.target.value)}>
            <option value="ALL">All Sentiments</option>
            <option value="POSITIVE">Positive (+)</option>
            <option value="NEGATIVE">Negative (-)</option>
            <option value="NEUTRAL">Neutral (~0)</option>
          </select>

          {/* Impact Slider */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            background: 'var(--bg-input)',
            padding: '0.4rem 0.65rem',
            borderRadius: '8px',
            border: '1px solid var(--border-medium)'
          }}>
            <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              Impact &ge; {minImpact.toFixed(1)}
            </span>
            <input
              type="range"
              min="1.0"
              max="9.0"
              step="0.5"
              value={minImpact}
              onChange={(e) => setMinImpact(parseFloat(e.target.value))}
              style={{ width: '60px', accentColor: 'var(--color-cyan)', cursor: 'pointer' }}
            />
          </div>

          {/* Source Filter */}
          <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
            <option value="ALL">All Sources</option>
            <option value="GDELT">GDELT Live</option>
            <option value="Kaggle">Kaggle PhraseBank</option>
          </select>

        </div>
      </div>

      {/* Signal Status Counter */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
        <span>Showing <strong style={{ color: '#FFFFFF' }}>{filteredSignals.length}</strong> of {signals.length} signals</span>
        {selectedCompany && (
          <button
            onClick={() => onSelectCompany('')}
            style={{ background: 'none', border: 'none', color: 'var(--color-cyan)', cursor: 'pointer', fontSize: '0.75rem' }}
          >
            Clear ticker filter ({selectedCompany})
          </button>
        )}
      </div>

      {/* Feed Table */}
      <div className="table-responsive" style={{ maxHeight: '480px' }}>
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Sentiment</th>
              <th>Event Classification</th>
              <th>Impact Score</th>
              <th>Risk Level</th>
              <th>Source</th>
              <th>Timestamp</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filteredSignals.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-tertiary)' }}>
                  No risk signals match the active filters.
                </td>
              </tr>
            ) : (
              filteredSignals.map((sig, idx) => (
                <tr
                  key={sig.id || idx}
                  onClick={() => onSelectCompany(sig.company)}
                  className={selectedCompany === sig.company ? 'selected-row' : ''}
                  style={{ cursor: 'pointer' }}
                >
                  
                  {/* Company */}
                  <td className="font-mono" style={{ fontWeight: 800 }}>
                    <span style={{
                      padding: '0.2rem 0.5rem',
                      borderRadius: '5px',
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-medium)',
                      color: 'var(--color-cyan)'
                    }}>
                      {sig.company}
                    </span>
                  </td>

                  {/* Sentiment */}
                  <td>
                    {getSentimentPill(sig.sentiment_score)}
                  </td>

                  {/* Event */}
                  <td>
                    <span style={{
                      padding: '0.2rem 0.5rem',
                      borderRadius: '5px',
                      background: 'rgba(18, 27, 48, 0.8)',
                      border: '1px solid var(--border-subtle)',
                      fontSize: '0.74rem',
                      color: 'var(--text-primary)',
                      fontWeight: 600
                    }}>
                      {sig.event_type}
                    </span>
                  </td>

                  {/* Impact */}
                  <td className="font-mono">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{
                        fontWeight: 700,
                        color: sig.impact_score >= 7.5 ? '#FB7185' : sig.impact_score >= 5.0 ? '#FBBF24' : 'var(--text-secondary)'
                      }}>
                        {sig.impact_score.toFixed(1)}/10
                      </span>
                      <div style={{ width: '45px', height: '5px', background: 'var(--bg-input)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${(sig.impact_score / 10) * 100}%`,
                          background: sig.impact_score >= 7.5 ? '#FB7185' : sig.impact_score >= 5.0 ? '#FBBF24' : 'var(--color-cyan)'
                        }} />
                      </div>
                    </div>
                  </td>

                  {/* Risk Level */}
                  <td>
                    {getRiskBadge(sig.risk_level)}
                  </td>

                  {/* Source */}
                  <td className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    {sig.source}
                  </td>

                  {/* Timestamp */}
                  <td className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                    {new Date(sig.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' +
                     new Date(sig.timestamp).toLocaleDateString([], { month: 'numeric', day: 'numeric' })}
                  </td>

                  {/* Inspect */}
                  <td style={{ textAlign: 'right' }}>
                    <ChevronRight size={14} style={{ color: 'var(--color-cyan)' }} />
                  </td>

                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
};
