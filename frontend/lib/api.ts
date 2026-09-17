const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${path} failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

export interface HealthResponse {
  status: string;
  app: string;
  environment: string;
  data_source_mode: string;
  live_series_status: Record<string, boolean> | null;
  timestamp: string;
}

export interface SeriesListResponse {
  series: string[];
  models: string[];
}

export interface ModelGovernance {
  model_name: string;
  model_version: string;
  data_period_start: string | null;
  data_period_end: string | null;
  forecast_horizon_days: number | null;
  confidence_level: number | null;
  generated_at: string;
  assumptions: string[];
  data_quality: string;
  random_seed: number | null;
}

export interface ForecastResponse {
  series_name: string;
  model: string;
  dates: string[];
  point_forecast: number[];
  lower_90: number[];
  upper_90: number[];
  governance: ModelGovernance;
}

export interface PricesResponse {
  data_quality: string;
  data_quality_by_series: Record<string, string>;
  live_status: Record<string, boolean> | null;
  dates: string[];
  series: Record<string, number[]>;
}

export interface FeedstockScenarioInput {
  feedstock: string;
  feedstock_price: number;
  throughput_tons_day: number;
  ethylene_price_usd_ton: number;
  propylene_price_usd_ton: number;
  byproduct_price_usd_ton: number;
  conversion_cost_usd_ton_feedstock: number;
  logistics_cost_usd_ton_feedstock: number;
  fx_usdinr?: number;
  operating_days?: number;
}

export interface FeedstockComparisonRow {
  rank: number;
  scenario: string;
  feedstock: string;
  ethylene_tons_day: number;
  propylene_tons_day: number;
  revenue_usd_day: number;
  feedstock_cost_usd_day: number;
  contribution_margin_usd_day: number;
  cm_usd_per_ton_ethylene: number;
  ebitda_usd_year: number;
  ebitda_inr_cr_year: number;
  margin_pct_of_revenue: number;
}

export function dataQualityLabel(q: string | undefined | null): string {
  switch (q) {
    case "real_validated":
      return "Live Market Data";
    case "real_unvalidated":
      return "Real Data (Unvalidated)";
    case "synthetic":
    default:
      return "Demo/Synthetic Data";
  }
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  seriesList: () => request<SeriesListResponse>("/api/forecasting/series"),
  prices: (series: string[], tailDays = 250) =>
    request<PricesResponse>(
      `/api/data/prices?${series.map((s) => `series=${encodeURIComponent(s)}`).join("&")}&tail_days=${tailDays}`
    ),
  forecast: (series_name: string, model: string, horizon_days: number) =>
    request<ForecastResponse>("/api/forecasting/forecast", {
      method: "POST",
      body: JSON.stringify({ series_name, model, horizon_days }),
    }),
  compareFeedstocks: (scenarios: Record<string, FeedstockScenarioInput>) =>
    request<{ comparison: FeedstockComparisonRow[] }>("/api/feedstock/compare", {
      method: "POST",
      body: JSON.stringify({ scenarios }),
    }),
};
