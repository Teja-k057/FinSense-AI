import type {
  SystemHealth,
  RiskSignalItem,
  NewsArticleItem,
  RebalanceSummary,
  BacktestComparisonResult,
  CompanyItem
} from '../types';

const API_BASE = 'http://localhost:8000/api/v1';

export async function fetchHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed with status ${res.status}`);
  const json = await res.json();
  return json.data || json;
}

export async function fetchLatestRebalance(): Promise<RebalanceSummary> {
  const res = await fetch(`${API_BASE}/rebalancer/latest`);
  if (!res.ok) throw new Error(`Failed to fetch latest rebalance: ${res.statusText}`);
  return await res.json();
}

export async function executeRebalance(params?: {
  max_weight_cap?: number;
  min_weight_floor?: number;
  turnover_penalty?: number;
}): Promise<RebalanceSummary> {
  const res = await fetch(`${API_BASE}/rebalancer/rebalance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params || {})
  });
  if (!res.ok) throw new Error(`Rebalance execution failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchRiskSignals(params?: {
  company?: string;
  min_impact?: number;
  limit?: number;
  offset?: number;
}): Promise<{ total: number; items: RiskSignalItem[] }> {
  const query = new URLSearchParams();
  if (params?.company) query.append('company', params.company);
  if (params?.min_impact !== undefined) query.append('min_impact', params.min_impact.toString());
  if (params?.limit) query.append('limit', params.limit.toString());
  if (params?.offset !== undefined) query.append('offset', params.offset.toString());

  const res = await fetch(`${API_BASE}/risk-signals?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch risk signals: ${res.statusText}`);
  return await res.json();
}

export async function fetchNewsArticles(params?: {
  company?: string;
  source?: string;
  limit?: number;
  offset?: number;
}): Promise<{ total: number; items: NewsArticleItem[] }> {
  const query = new URLSearchParams();
  if (params?.company) query.append('company', params.company);
  if (params?.source) query.append('source', params.source);
  if (params?.limit) query.append('limit', params.limit.toString());
  if (params?.offset !== undefined) query.append('offset', params.offset.toString());

  const res = await fetch(`${API_BASE}/news?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch news articles: ${res.statusText}`);
  return await res.json();
}

export async function fetchCompanies(): Promise<CompanyItem[]> {
  const res = await fetch(`${API_BASE}/companies`);
  if (!res.ok) throw new Error(`Failed to fetch companies: ${res.statusText}`);
  return await res.json();
}

export async function runHistoricalBacktest(params?: {
  start_date?: string;
  end_date?: string;
  rebalance_frequency?: 'DAILY' | 'WEEKLY' | 'MONTHLY';
}): Promise<BacktestComparisonResult> {
  const res = await fetch(`${API_BASE}/rebalancer/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_date: params?.start_date,
      end_date: params?.end_date,
      rebalance_frequency: params?.rebalance_frequency || 'WEEKLY'
    })
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Backtest failed: ${res.statusText}`);
  }
  return await res.json();
}

export async function ingestGdelt(): Promise<{ status: string; total_articles: number; signals_generated: number }> {
  const res = await fetch(`${API_BASE}/ingest/gdelt?limit=15`, { method: 'POST' });
  if (!res.ok) throw new Error(`GDELT ingestion failed: ${res.statusText}`);
  const json = await res.json();
  return json.data || json;
}

export async function ingestKaggle(): Promise<{ status: string; total_articles: number; signals_generated: number }> {
  const res = await fetch(`${API_BASE}/ingest/kaggle?limit=15`, { method: 'POST' });
  if (!res.ok) throw new Error(`Kaggle ingestion failed: ${res.statusText}`);
  const json = await res.json();
  return json.data || json;
}

export async function analyzeAdHocHeadline(text: string): Promise<RiskSignalItem> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, source: 'Analyst Terminal' })
  });
  if (!res.ok) throw new Error(`Ad-hoc analysis failed: ${res.statusText}`);
  return await res.json();
}
