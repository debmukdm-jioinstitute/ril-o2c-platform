"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Area,
} from "recharts";
import type { ForecastResponse, PricesResponse } from "@/lib/api";

interface Props {
  history: PricesResponse | null;
  seriesName: string;
  forecast: ForecastResponse | null;
}

export default function ForecastChart({ history, seriesName, forecast }: Props) {
  const historyPoints = history
    ? history.dates.map((d, i) => ({ date: d, actual: history.series[seriesName]?.[i] }))
    : [];
  const forecastPoints = forecast
    ? forecast.dates.map((d, i) => ({
        date: d,
        forecast: forecast.point_forecast[i],
        band: [forecast.lower_90[i], forecast.upper_90[i]] as [number, number],
      }))
    : [];
  const data = [...historyPoints, ...forecastPoints];

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94a3b8" }} minTickGap={40} />
        <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} domain={["auto", "auto"]} />
        <Tooltip
          contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }}
          labelStyle={{ color: "#e2e8f0" }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area
          type="monotone"
          dataKey="band"
          name="90% interval"
          stroke="none"
          fill="#1d9bf0"
          fillOpacity={0.15}
        />
        <Line type="monotone" dataKey="actual" name="Historical (synthetic)" stroke="#94a3b8" dot={false} strokeWidth={1.5} />
        <Line type="monotone" dataKey="forecast" name="Forecast" stroke="#1d9bf0" dot={false} strokeWidth={2} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
