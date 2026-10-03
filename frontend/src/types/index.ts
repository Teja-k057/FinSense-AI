export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type RebalanceAction = 'INCREASE' | 'HOLD' | 'REDUCE';

export interface SystemHealth {
  status: string;
  app_name: string;
  environment: string;
  database_status: string;
  models_ready: boolean;
}

export interface RiskSignalItem {
  id: string;
  company: string;
  document_id?: string;
  sentiment_score: number;
  sentiment_label?: string;
  event_type: string;
  impact_score: number;
  risk_level: RiskLevel;
  explanation: string;
  source: string;
  timestamp: string;
  article_title?: string;
}

export interface NewsArticleItem {
  id: string;
  source: string;
  title: string;
  text: string;
  url?: string;
  publication_time: string;
  retrieved_time: string;
  company_entities?: string[];
  domain?: string;
  original_label?: string;
}

export interface ConstituentRebalanceDetail {
  ticker: string;
  company_name: string;
  sector: string;
  current_price: number;
  current_index_weight: number;
  current_weight_pct: number;
  target_weight: number;
  target_weight_pct: number;
  weight_delta_pct: number;
  recent_return: number;
  volatility?: number;
  latest_sentiment_score: number;
  latest_impact_score: number;
  latest_event_type: string;
  calculated_risk_signal: number;
  rebalance_action: RebalanceAction;
  explanation: string;
}

export interface RebalanceSummary {
  as_of: string;
  universe_size: number;
  total_current_weight_pct: number;
  total_target_weight_pct: number;
  turnover_pct: number;
  actions_count: {
    INCREASE: number;
    HOLD: number;
    REDUCE: number;
  };
  average_sentiment: number;
  average_impact: number;
  top_increased: Array<{ ticker: string; delta_pct: number; target_weight_pct: number }>;
  top_reduced: Array<{ ticker: string; delta_pct: number; target_weight_pct: number }>;
  constituents: ConstituentRebalanceDetail[];
  methodology: string;
}

export interface BacktestMetrics {
  cumulative_return_pct: number;
  annualized_return_pct: number;
  annualized_volatility_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  total_turnover_pct: number;
  win_rate_pct: number;
}

export interface BacktestTrajectoryPoint {
  period_index: number;
  date: string;
  rebalance_date: string;
  subsequent_date: string;
  baseline_period_return_pct: number;
  nlp_period_return_pct: number;
  active_period_return_pct: number;
  baseline_cumulative_return_pct: number;
  nlp_cumulative_return_pct: number;
  turnover_pct: number;
  transaction_cost_pct: number;
  top_overweight: string[];
  top_underweight: string[];
  news_signals_used: number;
}

export interface BacktestComparisonResult {
  as_of: string;
  start_date: string;
  end_date: string;
  rebalance_frequency: string;
  total_periods: number;
  universe_size: number;
  baseline_metrics: BacktestMetrics;
  nlp_strategy_metrics: BacktestMetrics;
  outperformance_pct: number;
  trajectory: BacktestTrajectoryPoint[];
  assumptions: Record<string, any> | string[];
  limitations: string[];
  disclaimer: string;
}

export interface CompanyItem {
  ticker: string;
  name: string;
  sector: string;
  market_price: number;
  price_change_pct: number;
  base_weight_pct: number;
  signal_count: number;
  average_sentiment: number;
  average_impact: number;
  risk_level: RiskLevel;
}
