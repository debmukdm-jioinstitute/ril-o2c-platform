"use client";

import { useEffect, useMemo, useState } from "react";
import ForecastChart from "@/components/ForecastChart";
import FeedstockTable from "@/components/FeedstockTable";
import PageHeader from "@/components/layout/PageHeader";
import StatCard from "@/components/StatCard";
import {
  api,
  dataQualityLabel,
  type FeedstockComparisonRow,
  type ForecastResponse,
  type HealthResponse,
  type PricesResponse,
  type SeriesListResponse,
} from "@/lib/api";

const SERIES_META: Record<string, { label: string; unit: string }> = {
  crude_brent_usd_bbl: { label: "Brent Crude Oil", unit: "USD/bbl" },
  ethane_usd_mmbtu: { label: "Ethane", unit: "USD/MMBtu" },
  naphtha_usd_ton: { label: "Naphtha", unit: "USD/ton" },
  propane_usd_ton: { label: "Propane", unit: "USD/ton" },
  butane_usd_ton: { label: "Butane", unit: "USD/ton" },
  natural_gas_usd_mmbtu: { label: "Natural Gas (Henry Hub)", unit: "USD/MMBtu" },
  ethylene_usd_ton: { label: "Ethylene", unit: "USD/ton" },
  propylene_usd_ton: { label: "Propylene", unit: "USD/ton" },
  fx_usdinr: { label: "USD/INR Exchange Rate", unit: "INR" },
};

const FEEDSTOCK_PRICE_SERIES = ["ethane_usd_mmbtu", "naphtha_usd_ton", "propane_usd_ton", "butane_usd_ton", "fx_usdinr"];
const FEEDSTOCK_TO_SERIES: Record<string, string> = {
  ethane: "ethane_usd_mmbtu",
  naphtha: "naphtha_usd_ton",
  propane: "propane_usd_ton",
  butane: "butane_usd_ton",
};
const LIVE_SERIES = new Set(["crude_brent_usd_bbl", "natural_gas_usd_mmbtu", "propane_usd_ton", "fx_usdinr"]);

function fmtPrice(n: number | undefined, digits = 1): string {
  if (n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [seriesList, setSeriesList] = useState<SeriesListResponse | null>(null);
  const [seriesName, setSeriesName] = useState("crude_brent_usd_bbl");
  const [model, setModel] = useState("ensemble");
  const [horizon, setHorizon] = useState(90);
  const [runKey, setRunKey] = useState(0);
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
    Promise.all([api.prices([seriesName], 400), api.forecast(seriesName, model, horizon)])
      .then(([h, f]) => {
        setHistory(h);
        setForecast(f);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [seriesName, model, horizon, runKey]);

  useEffect(() => {
    api
      .prices(FEEDSTOCK_PRICE_SERIES, 1)
      .then((latest) => {
        const qualityByFeedstock = Object.fromEntries(
          Object.entries(FEEDSTOCK_TO_SERIES).map(([feedstock, series]) => [feedstock, latest.data_quality_by_series[series]])
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
    return q ? dataQualityLabel(q) : null;
  }, [history, forecast]);

  const meta = SERIES_META[seriesName] ?? { label: seriesName, unit: "" };

  const currentPrice = history ? history.series[seriesName]?.[history.series[seriesName].length - 1] : undefined;
  const previousPrice = history ? history.series[seriesName]?.[history.series[seriesName].length - 2] : undefined;
  const currentDeltaPct =
    currentPrice !== undefined && previousPrice ? ((currentPrice - previousPrice) / previousPrice) * 100 : undefined;

  const forecastEnd = forecast?.point_forecast[forecast.point_forecast.length - 1];
  const forecastDeltaPct =
    forecastEnd !== undefined && currentPrice ? ((forecastEnd - currentPrice) / currentPrice) * 100 : undefined;

  const rangeLow = forecast?.lower_90[forecast.lower_90.length - 1];
  const rangeHigh = forecast?.upper_90[forecast.upper_90.length - 1];

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        section="Market Forecasting"
        title="Probabilistic Digital Twin — Petrochemical Economics & Market Forecasting"
        subtitle="Research prototype. Complements the existing LP optimizer — does not replace it."
        badge="Research Prototype"
      />

      {error && (
        <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">{error}</div>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-line bg-white p-4 shadow-card">
        <span className="text-xs font-semibold uppercase tracking-wide text-ink-400">Market Forecasting Engine</span>
        <select
          value={seriesName}
          onChange={(e) => setSeriesName(e.target.value)}
          className="rounded-lg border border-line bg-cream-50 px-3 py-1.5 text-sm text-ink-700 focus:border-gold-400 focus:outline-none"
        >
          {(seriesList?.series ?? [seriesName]).map((s) => (
            <option key={s} value={s}>
              {(SERIES_META[s]?.label ?? s) + (LIVE_SERIES.has(s) ? " (live)" : "")}
            </option>
          ))}
        </select>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="rounded-lg border border-line bg-cream-50 px-3 py-1.5 text-sm text-ink-700 focus:border-gold-400 focus:outline-none"
        >
          {(seriesList?.models ?? [model]).map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-ink-500">
          Horizon (days)
          <input
            type="number"
            min={1}
            max={365}
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
            className="w-20 rounded-lg border border-line bg-cream-50 px-3 py-1.5 text-sm text-ink-700 focus:border-gold-400 focus:outline-none"
          />
        </label>
        <button
          onClick={() => setRunKey((k) => k + 1)}
          disabled={loading}
          className="ml-auto flex items-center gap-2 rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-ink-700 disabled:opacity-50"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
          {loading ? "Running…" : "Run Forecast"}
        </button>
      </div>

      <div className="rounded-xl border border-line bg-white p-5 shadow-card">
        <div className="mb-2 flex items-start justify-between">
          <h2 className="text-base font-semibold text-ink-700">{meta.label} Price Forecast</h2>
          <div className="flex items-center gap-3 text-xs text-ink-400">
            {forecast && (
              <span>
                Last updated: {new Date(forecast.governance.generated_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
              </span>
            )}
            <span>·</span>
            <span className={dataQualityBadge === "Live Market Data" ? "font-medium text-emerald-600" : "font-medium text-gold-600"}>
              Data source: {dataQualityBadge === "Live Market Data" ? "Live" : "Internal / Synthetic"}
            </span>
          </div>
        </div>
        <p className="mb-1 text-xs text-ink-400">{meta.unit}</p>
        <ForecastChart history={history} seriesName={seriesName} forecast={forecast} />
        {forecast && (
          <ul className="mt-3 list-disc pl-5 text-xs text-ink-400">
            {forecast.governance.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          label="Current Price"
          value={fmtPrice(currentPrice)}
          unit={meta.unit}
          delta={currentDeltaPct !== undefined ? `${Math.abs(currentDeltaPct).toFixed(1)}%` : undefined}
          deltaLabel="vs previous close"
          deltaDirection={currentDeltaPct === undefined ? "neutral" : currentDeltaPct >= 0 ? "up" : "down"}
        />
        <StatCard
          label={`Forecast (${horizon} days)`}
          value={fmtPrice(forecastEnd)}
          unit={meta.unit}
          delta={forecastDeltaPct !== undefined ? `${Math.abs(forecastDeltaPct).toFixed(1)}%` : undefined}
          deltaLabel="vs current"
          deltaDirection={forecastDeltaPct === undefined ? "neutral" : forecastDeltaPct >= 0 ? "up" : "down"}
        />
        <StatCard
          label="90% Forecast Range"
          value={rangeLow !== undefined && rangeHigh !== undefined ? `${fmtPrice(rangeLow, 1)} – ${fmtPrice(rangeHigh, 1)}` : "—"}
          unit={meta.unit}
          delta="At horizon end"
          deltaDirection="neutral"
        />
        <StatCard label="Model" value={forecast?.governance.model_name ?? model} delta="Research prototype" deltaDirection="neutral" />
      </div>

      <div className="mt-10">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">Feedstock Economics — Base-Case Comparison</h2>
        </div>
        {feedstockRows.length > 0 ? (
          <FeedstockTable rows={feedstockRows} qualityByFeedstock={feedstockQuality} />
        ) : (
          <p className="text-sm text-ink-400">Loading feedstock comparison…</p>
        )}
        <p className="mt-2 text-xs text-ink-400">
          Ranking is computed from the prices and cost assumptions above — no feedstock is assumed structurally superior. Propane
          and FX prices are live (EIA / ECB reference rate); ethane, naphtha, and butane have no free public spot-price source and
          remain clearly-labeled synthetic — see the dot on each row.
        </p>
      </div>
    </div>
  );
}
