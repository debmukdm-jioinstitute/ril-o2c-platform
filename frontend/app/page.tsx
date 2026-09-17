"use client";

import { useEffect, useMemo, useState } from "react";
import ForecastChart from "@/components/ForecastChart";
import FeedstockTable from "@/components/FeedstockTable";
import {
  api,
  dataQualityLabel,
  type FeedstockComparisonRow,
  type ForecastResponse,
  type HealthResponse,
  type PricesResponse,
  type SeriesListResponse,
} from "@/lib/api";

// Series pulled to build the feedstock comparison scenarios. crude_brent_usd_bbl and
// natural_gas_usd_mmbtu aren't directly used as a feedstock price but are fetched alongside so
// the /api/data/prices data_quality_by_series map is available for every series in one call.
const FEEDSTOCK_PRICE_SERIES = ["ethane_usd_mmbtu", "naphtha_usd_ton", "propane_usd_ton", "butane_usd_ton", "fx_usdinr"];
const FEEDSTOCK_TO_SERIES: Record<string, string> = {
  ethane: "ethane_usd_mmbtu",
  naphtha: "naphtha_usd_ton",
  propane: "propane_usd_ton",
  butane: "butane_usd_ton",
};
// Mirrors data.adapters.live_market.LIVE_SERIES — kept in sync manually since it's a small,
// stable list; annotates the series dropdown so live vs. synthetic is visible before fetching.
const LIVE_SERIES = new Set(["crude_brent_usd_bbl", "natural_gas_usd_mmbtu", "propane_usd_ton", "fx_usdinr"]);

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [seriesList, setSeriesList] = useState<SeriesListResponse | null>(null);
  const [seriesName, setSeriesName] = useState("crude_brent_usd_bbl");
  const [model, setModel] = useState("ensemble");
  const [horizon, setHorizon] = useState(90);
  const [history, setHistory] = useState<PricesResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [feedstockRows, setFeedstockRows] = useState<FeedstockComparisonRow[]>([]);
  const [feedstockQuality, setFeedstockQuality] = useState<Record<string, string>>({});
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
    // Pull the latest value of every feedstock-relevant series (and FX) in one call, so the
    // comparison table uses live prices for whichever series genuinely have them (propane, FX)
    // and the synthetic generator's current value for the rest (ethane, naphtha, butane) —
    // never a stale hardcoded constant either way.
    api
      .prices(FEEDSTOCK_PRICE_SERIES, 1)
      .then((latest) => {
        const qualityByFeedstock = Object.fromEntries(
          Object.entries(FEEDSTOCK_TO_SERIES).map(([feedstock, series]) => [
            feedstock,
            latest.data_quality_by_series[series],
          ])
        );
        setFeedstockQuality(qualityByFeedstock);
        const latestValue = (series: string) => latest.series[series]?.[latest.series[series].length - 1];
        const fx = latestValue("fx_usdinr") ?? 83.5;

        const scenarios = Object.fromEntries(
          Object.entries(FEEDSTOCK_TO_SERIES).map(([feedstock, series]) => [
            feedstock,
            {
              feedstock,
              feedstock_price: latestValue(series),
              throughput_tons_day: 3000,
              ethylene_price_usd_ton: 950,
              propylene_price_usd_ton: 900,
              byproduct_price_usd_ton: 500,
              conversion_cost_usd_ton_feedstock: 60,
              logistics_cost_usd_ton_feedstock: 15,
              fx_usdinr: fx,
            },
          ])
        );
        return api.compareFeedstocks(scenarios);
      })
      .then((r) => setFeedstockRows(r.comparison))
      .catch((e) => setError(String(e)));
  }, []);

  const dataQualityBadge = useMemo(() => {
    const q = forecast?.governance.data_quality ?? history?.data_quality;
    if (!q) return null;
    return dataQualityLabel(q);
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
            <span
              className={
                "mt-2 inline-block rounded-full border px-2 py-0.5 " +
                (dataQualityBadge === "Live Market Data"
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                  : "border-amber-500/40 bg-amber-500/10 text-amber-400")
              }
            >
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
                {LIVE_SERIES.has(s) ? " (live)" : ""}
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
          <FeedstockTable rows={feedstockRows} qualityByFeedstock={feedstockQuality} />
        ) : (
          <p className="text-sm text-slate-500">Loading feedstock comparison…</p>
        )}
        <p className="mt-2 text-xs text-slate-500">
          Ranking is computed from the prices and cost assumptions above — no feedstock is assumed
          structurally superior. Adjust assumptions via the API to see the ranking respond.
          Propane and FX prices are live (EIA / ECB reference rate); ethane, naphtha, and butane
          have no free public spot-price source (OPIS/Platts-only) and remain clearly-labeled
          synthetic — see the badge on each row.
        </p>
      </section>
    </main>
  );
}
