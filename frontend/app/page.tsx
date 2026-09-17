"use client";

import { useEffect, useMemo, useState } from "react";
import ForecastChart from "@/components/ForecastChart";
import FeedstockTable from "@/components/FeedstockTable";
import {
  api,
  type FeedstockComparisonRow,
  type ForecastResponse,
  type HealthResponse,
  type PricesResponse,
  type SeriesListResponse,
} from "@/lib/api";

const FEEDSTOCK_BASE_PRICES: Record<string, number> = {
  ethane: 8.5,
  naphtha: 640,
  propane: 520,
  butane: 540,
};

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [seriesList, setSeriesList] = useState<SeriesListResponse | null>(null);
  const [seriesName, setSeriesName] = useState("crude_brent_usd_bbl");
  const [model, setModel] = useState("ensemble");
  const [horizon, setHorizon] = useState(90);
  const [history, setHistory] = useState<PricesResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [feedstockRows, setFeedstockRows] = useState<FeedstockComparisonRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(String(e)));
    api.seriesList().then(setSeriesList).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.prices([seriesName], 400),
      api.forecast(seriesName, model, horizon),
    ])
      .then(([h, f]) => {
        setHistory(h);
        setForecast(f);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [seriesName, model, horizon]);

  useEffect(() => {
    const scenarios = Object.fromEntries(
      Object.entries(FEEDSTOCK_BASE_PRICES).map(([feedstock, price]) => [
        feedstock,
        {
          feedstock,
          feedstock_price: price,
          throughput_tons_day: 3000,
          ethylene_price_usd_ton: 950,
          propylene_price_usd_ton: 900,
          byproduct_price_usd_ton: 500,
          conversion_cost_usd_ton_feedstock: 60,
          logistics_cost_usd_ton_feedstock: 15,
        },
      ])
    );
    api
      .compareFeedstocks(scenarios)
      .then((r) => setFeedstockRows(r.comparison))
      .catch((e) => setError(String(e)));
  }, []);

  const dataQualityBadge = useMemo(() => {
    const q = history?.data_quality ?? forecast?.governance.data_quality;
    if (!q) return null;
    return q === "synthetic" ? "Demo/Synthetic Data" : q;
  }, [history, forecast]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <header className="mb-8 flex items-start justify-between border-b border-slate-800 pb-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-accent">
            RIL O2C AI Decision Intelligence Platform
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-100">
            Probabilistic Digital Twin — Petrochemical Economics &amp; Market Forecasting
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Research prototype. Complements the existing LP optimizer — does not replace it.
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
          <div>{health ? health.status.toUpperCase() : "connecting…"}</div>
          <div>{health?.environment}</div>
          {dataQualityBadge && (
            <span className="mt-2 inline-block rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-amber-400">
              {dataQualityBadge}
            </span>
          )}
        </div>
      </header>

      {error && (
        <div className="mb-6 rounded border border-rose-800 bg-rose-950/50 px-4 py-2 text-sm text-rose-300">
          {error}
        </div>
      )}

      <section className="mb-10">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
            Market Forecasting Engine
          </h2>
          <select
            value={seriesName}
            onChange={(e) => setSeriesName(e.target.value)}
            className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200"
          >
            {(seriesList?.series ?? [seriesName]).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200"
          >
            {(seriesList?.models ?? [model]).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-slate-400">
            Horizon (days)
            <input
              type="number"
              min={1}
              max={365}
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="w-20 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200"
            />
          </label>
          {loading && <span className="text-xs text-slate-500">loading…</span>}
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
          <ForecastChart history={history} seriesName={seriesName} forecast={forecast} />
        </div>

        {forecast && (
          <div className="mt-3 text-xs text-slate-500">
            Model: <span className="text-slate-300">{forecast.governance.model_name}</span> ·
            Data period: {forecast.governance.data_period_start} → {forecast.governance.data_period_end} ·
            90% confidence interval · Generated {new Date(forecast.governance.generated_at).toLocaleString()}
            <ul className="mt-1 list-disc pl-5">
              {forecast.governance.assumptions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-300">
          Feedstock Economics — Base-Case Comparison
        </h2>
        {feedstockRows.length > 0 ? (
          <FeedstockTable rows={feedstockRows} />
        ) : (
          <p className="text-sm text-slate-500">Loading feedstock comparison…</p>
        )}
        <p className="mt-2 text-xs text-slate-500">
          Ranking is computed from the prices and cost assumptions above — no feedstock is assumed
          structurally superior. Adjust assumptions via the API to see the ranking respond.
        </p>
      </section>
    </main>
  );
}
