import React, { useState } from 'react';
import { 
  X, 
  Sparkles, 
  Cpu 
} from 'lucide-react';
import { analyzeAdHocHeadline } from '../services/api';
import type { RiskSignalItem } from '../types';

interface AdHocAnalyzerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSignalAdded?: (sig: RiskSignalItem) => void;
}

export const AdHocAnalyzerModal: React.FC<AdHocAnalyzerModalProps> = ({
  isOpen,
  onClose,
  onSignalAdded
}) => {
  const [headline, setHeadline] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RiskSignalItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const sampleHeadlines = [
    "Apple supplier factory faces severe disruption and supply chain shutdown.",
    "JPMorgan posts blowout quarterly earnings with record investment banking fees.",
    "NVIDIA faces immediate semiconductor export restrictions and regulatory probe.",
    "ExxonMobil announces major Gulf of Mexico oil discovery boosting reserves.",
    "Boeing 737 Max production delayed over quality audit and FAA safety review."
  ];

  const handleAnalyze = async () => {
    if (!headline.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const sig = await analyzeAdHocHeadline(headline);
      setResult(sig);
      if (onSignalAdded) onSignalAdded(sig);
    } catch (err: any) {
      setError(err.message || 'Analysis failed. Please check the backend service.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 100,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1rem',
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)'
    }}>
      <div className="card" style={{
        maxWidth: '680px',
        width: '100%',
        background: '#0D1424',
        border: '1px solid var(--border-medium)',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.8)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem'
      }}>
        
        {/* Header */}
        <div className="card-header" style={{ margin: 0, paddingBottom: '0.75rem' }}>
          <div className="card-title-group">
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
              <Cpu size={18} />
            </div>
            <div>
              <div className="card-title">Live NLP Headline & Event Risk Analyzer</div>
              <div className="card-subtitle">
                Test the Unified NLP Risk Engine & Tactical Rebalance Impact in real time.
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', padding: '0.25rem' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Text Area */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
            News Headline or Financial Text:
          </label>
          <textarea
            rows={3}
            value={headline}
            onChange={(e) => setHeadline(e.target.value)}
            placeholder="e.g. Apple faces severe supply chain disruptions following factory shutdown..."
            style={{ width: '100%', resize: 'vertical' }}
          />
        </div>

        {/* Sample Headline Chips */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-tertiary)' }}>
            Quick Test Samples:
          </span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
            {sampleHeadlines.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setHeadline(sample)}
                style={{
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '0.25rem 0.55rem',
                  fontSize: '0.7rem',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
              >
                {sample.substring(0, 42)}...
              </button>
            ))}
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.65rem' }}>
          <button type="button" onClick={onClose} className="btn btn-secondary">
            Close
          </button>
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={loading || !headline.trim()}
            className="btn btn-primary"
          >
            <Sparkles size={14} className={loading ? 'animate-spin' : ''} />
            <span>{loading ? 'Evaluating NLP Model...' : 'Analyze Risk Signal'}</span>
          </button>
        </div>

        {error && (
          <div style={{ padding: '0.75rem', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', borderRadius: '8px', color: '#FB7185', fontSize: '0.78rem' }}>
            {error}
          </div>
        )}

        {/* Result Card */}
        {result && (
          <div style={{
            background: 'var(--bg-input)',
            padding: '1rem',
            borderRadius: '12px',
            border: '1px solid var(--border-active)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <span className="font-mono" style={{
                  padding: '0.25rem 0.65rem',
                  borderRadius: '6px',
                  background: 'var(--bg-surface-elevated)',
                  border: '1px solid var(--border-medium)',
                  fontWeight: 800,
                  color: 'var(--color-cyan)'
                }}>
                  {result.company}
                </span>
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#FFFFFF' }}>Detected: {result.company}</div>
                  <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>Event: {result.event_type}</div>
                </div>
              </div>

              <span className={`badge ${
                result.risk_level === 'CRITICAL' ? 'badge-rose' :
                result.risk_level === 'HIGH' ? 'badge-amber' :
                result.risk_level === 'MEDIUM' ? 'badge-cyan' : 'badge-slate'
              }`}>
                {result.risk_level} RISK
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
              <div style={{ background: 'var(--bg-surface)', padding: '0.5rem', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Sentiment</span>
                <div className="font-mono" style={{
                  fontSize: '0.95rem',
                  fontWeight: 800,
                  marginTop: '0.15rem',
                  color: result.sentiment_score > 0.05 ? '#34D399' : result.sentiment_score < -0.05 ? '#FB7185' : 'var(--text-secondary)'
                }}>
                  {result.sentiment_score >= 0 ? '+' : ''}{result.sentiment_score.toFixed(2)}
                </div>
              </div>

              <div style={{ background: 'var(--bg-surface)', padding: '0.5rem', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Impact Score</span>
                <div className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 800, color: '#FBBF24', marginTop: '0.15rem' }}>
                  {result.impact_score.toFixed(1)}/10
                </div>
              </div>

              <div style={{ background: 'var(--bg-surface)', padding: '0.5rem', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Tactical Action</span>
                <div className="font-mono" style={{
                  fontSize: '0.95rem',
                  fontWeight: 800,
                  marginTop: '0.15rem',
                  color: result.sentiment_score > 0.1 ? '#34D399' : result.sentiment_score < -0.1 ? '#FB7185' : 'var(--text-secondary)'
                }}>
                  {result.sentiment_score > 0.1 ? 'INCREASE' : result.sentiment_score < -0.1 ? 'REDUCE' : 'HOLD'}
                </div>
              </div>
            </div>

            <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-primary)', lineHeight: 1.5, background: 'rgba(0,0,0,0.2)', padding: '0.65rem', borderRadius: '8px' }}>
              <strong>Generated Explanation:</strong> {result.explanation}
            </p>
          </div>
        )}

      </div>
    </div>
  );
};
