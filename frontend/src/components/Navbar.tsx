import React from 'react';
import { 
  TrendingUp, 
  RotateCw, 
  Layers, 
  Search, 
  Sparkles,
  BarChart3,
  ListFilter,
  Radio,
  History
} from 'lucide-react';
import type { SystemHealth, ConstituentRebalanceDetail } from '../types';

interface NavbarProps {
  health: SystemHealth | null;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  constituents: ConstituentRebalanceDetail[];
  selectedTicker: string;
  onSelectTicker: (ticker: string) => void;
  onTriggerRebalance: () => void;
  onOpenAdHocModal: () => void;
  onRefreshAll: () => void;
  isRebalancing: boolean;
  isRefreshing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  activeTab,
  setActiveTab,
  constituents,
  selectedTicker,
  onSelectTicker,
  onTriggerRebalance,
  onOpenAdHocModal,
  onRefreshAll,
  isRebalancing,
  isRefreshing
}) => {
  const tabs = [
    { id: 'dashboard', label: 'Executive Dashboard', icon: BarChart3 },
    { id: 'composition', label: 'Constituents & Weights', icon: Layers },
    { id: 'feed', label: 'Live Risk Feed', icon: Radio },
    { id: 'backtest', label: 'Historical Backtest', icon: History },
  ];

  return (
    <div style={{ position: 'sticky', top: 0, zIndex: 50 }}>
      
      {/* 1. Live Market Ticker Tape */}
      <div className="ticker-tape-container">
        <span style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--color-cyan)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          MOCK 15 INDEX:
        </span>
        {(constituents || []).map((c) => {
          const isUp = (c.weight_delta_pct || 0) > 0.05;
          const isDown = (c.weight_delta_pct || 0) < -0.05;
          const isSelected = selectedTicker === c.ticker;

          return (
            <div
              key={c.ticker}
              onClick={() => onSelectTicker(c.ticker)}
              className={`ticker-item ${isSelected ? 'active' : ''}`}
            >
              <span className="symbol font-mono">{c.ticker}</span>
              <span className="price font-mono">${c.current_price != null ? c.current_price.toFixed(1) : '--'}</span>
              <span className={`font-mono ${isUp ? 'delta-up' : isDown ? 'delta-down' : ''}`} style={{ fontSize: '0.72rem' }}>
                {isUp ? '▲ +' : isDown ? '▼ ' : '— '}{(c.weight_delta_pct || 0).toFixed(2)}%
              </span>
            </div>
          );
        })}
      </div>

      {/* 2. Main Navigation Bar */}
      <header className="header-nav">
        
        {/* Brand Group */}
        <div className="brand-section">
          <div className="brand-icon">
            <TrendingUp size={22} />
          </div>
          <div>
            <div className="brand-title">
              <span>S&P Global × CRISIL</span>
              <span className="badge badge-cyan" style={{ fontSize: '0.65rem', padding: '0.15rem 0.5rem' }}>
                MODULE A
              </span>
            </div>
            <div className="brand-subtitle">
              Tactical High-Frequency Stock Index Rebalancer
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="view-tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`view-tab-btn ${isActive ? 'active' : ''}`}
              >
                <Icon size={15} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Action Controls */}
        <div className="header-actions">
          
          {/* Health Status Indicator */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.35rem 0.75rem',
            borderRadius: '8px',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.72rem',
            fontFamily: 'monospace'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: health?.database_status === 'connected' ? 'var(--color-emerald)' : 'var(--color-rose)',
              boxShadow: health?.database_status === 'connected' ? '0 0 8px var(--color-emerald)' : 'none'
            }} />
            <span style={{ color: 'var(--text-secondary)' }}>
              {health?.database_status === 'connected' ? 'POSTGRES / SQLITE' : 'DB OFFLINE'}
            </span>
          </div>

          {/* Ad-Hoc Analyzer Button */}
          <button
            onClick={onOpenAdHocModal}
            className="btn btn-secondary"
            title="Analyze custom news headline or event against NLP Engine"
          >
            <Search size={14} style={{ color: 'var(--color-cyan)' }} />
            <span>Ad-Hoc Analyzer</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefreshAll}
            disabled={isRefreshing}
            className="btn btn-secondary"
            style={{ padding: '0.55rem' }}
            title="Refresh prices and signals from API"
          >
            <RotateCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
          </button>

          {/* Trigger Rebalance Button */}
          <button
            onClick={onTriggerRebalance}
            disabled={isRebalancing}
            className="btn btn-rebalance"
          >
            <Layers size={14} className={isRebalancing ? 'animate-spin' : ''} />
            <span>{isRebalancing ? 'Optimizing Weights...' : 'Trigger Rebalance'}</span>
          </button>

        </div>

      </header>

    </div>
  );
};
