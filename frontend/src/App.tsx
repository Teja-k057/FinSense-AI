import { useState, useEffect } from 'react';
import { 
  AlertCircle, 
  CheckCircle 
} from 'lucide-react';

import { 
  fetchHealth, 
  fetchLatestRebalance, 
  executeRebalance, 
  fetchRiskSignals, 
  fetchNewsArticles, 
  runHistoricalBacktest 
} from './services/api';

import type { 
  SystemHealth, 
  RebalanceSummary, 
  RiskSignalItem, 
  NewsArticleItem, 
  BacktestComparisonResult 
} from './types';

import { FinSenseDashboard } from './components/FinSenseDashboard';
import { AdHocAnalyzerModal } from './components/AdHocAnalyzerModal';

export default function App() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [rebalanceSummary, setRebalanceSummary] = useState<RebalanceSummary | null>(null);
  const [signals, setSignals] = useState<RiskSignalItem[]>([]);
  const [newsArticles, setNewsArticles] = useState<NewsArticleItem[]>([]);
  const [backtestResult, setBacktestResult] = useState<BacktestComparisonResult | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string>('NVDA');

  // Loading and action states
  const [isRebalancing, setIsRebalancing] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [isAdHocModalOpen, setIsAdHocModalOpen] = useState(false);

  useEffect(() => {
    loadAllData();
  }, []);

  const showToast = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadAllData = async () => {
    try {
      // 1. Health
      fetchHealth().then(setHealth).catch(() => null);

      // 2. Latest Rebalance
      fetchLatestRebalance().then(reb => {
        if (reb) setRebalanceSummary(reb);
      }).catch(() => null);

      // 3. Signals
      fetchRiskSignals({ limit: 60 }).then(data => {
        if (data?.items) setSignals(data.items);
      }).catch(() => null);

      // 4. News
      fetchNewsArticles({ limit: 30 }).then(data => {
        if (data?.items) setNewsArticles(data.items);
      }).catch(() => null);

      // 5. Backtest
      runHistoricalBacktest({ rebalance_frequency: 'WEEKLY' }).then(bt => {
        if (bt) setBacktestResult(bt);
      }).catch(() => null);

    } catch (err: any) {
      console.error('Initialization error:', err);
    }
  };

  const handleTriggerRebalance = async () => {
    setIsRebalancing(true);
    try {
      const updated = await executeRebalance();
      setRebalanceSummary(updated);
      showToast(`Tactical Rebalance executed! Turnover: ${updated.turnover_pct.toFixed(2)}%`, 'success');
      
      const sigData = await fetchRiskSignals({ limit: 60 });
      if (sigData?.items) setSignals(sigData.items);
    } catch (err: any) {
      console.error('Rebalance execution failed:', err);
      showToast(`Rebalance failed: ${err.message}`, 'error');
    } finally {
      setIsRebalancing(false);
    }
  };

  return (
    <>
      {/* Toast Alert */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 100,
          padding: '0.85rem 1.25rem',
          borderRadius: '12px',
          border: '1px solid',
          borderColor: toastMessage.type === 'success' ? '#10B981' : toastMessage.type === 'error' ? '#EF4444' : '#2563EB',
          background: 'rgba(12, 18, 30, 0.95)',
          backdropFilter: 'blur(12px)',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.8)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.65rem',
          fontSize: '0.8rem',
          color: '#FFFFFF'
        }}>
          {toastMessage.type === 'success' ? <CheckCircle size={16} color="#34D399" /> : <AlertCircle size={16} color="#F87171" />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Main FinSense AI Dashboard */}
      <FinSenseDashboard
        summary={rebalanceSummary}
        signals={signals}
        news={newsArticles}
        backtest={backtestResult}
        onTriggerRebalance={handleTriggerRebalance}
        isRebalancing={isRebalancing}
        onSelectTicker={setSelectedTicker}
        selectedTicker={selectedTicker}
      />

      {/* Interactive Ad-Hoc Analyzer Modal */}
      <AdHocAnalyzerModal
        isOpen={isAdHocModalOpen}
        onClose={() => setIsAdHocModalOpen(false)}
        onSignalAdded={(newSig) => {
          setSignals(prev => [newSig, ...prev]);
          showToast(`Signal for ${newSig.company} evaluated!`, 'success');
        }}
      />
    </>
  );
}
