"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  ComposedChart,
  ReferenceLine,
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
  const forecastStart = forecast?.dates[0];

  return (
    <ResponsiveContainer width="100%" height={360}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e0d3" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#8892a8" }} minTickGap={40} axisLine={{ stroke: "#e5e0d3" }} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: "#8892a8" }} domain={["auto", "auto"]} axisLine={{ stroke: "#e5e0d3" }} tickLine={false} />
        <Tooltip
          contentStyle={{ background: "#ffffff", border: "1px solid #e5e0d3", fontSize: 12, borderRadius: 8 }}
          labelStyle={{ color: "#16233f", fontWeight: 600 }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "#5b6786" }} iconType="circle" />
        {forecastStart && (
          <ReferenceLine
            x={forecastStart}
            stroke="#b8860f"
            strokeDasharray="4 3"
            label={{ value: "Forecast (Start)", position: "insideTopRight", fill: "#a4740f", fontSize: 11 }}
          />
        )}
        <Area type="monotone" dataKey="band" name="90% interval" stroke="none" fill="#b8860f" fillOpacity={0.18} />
        <Line type="monotone" dataKey="actual" name="Historical (synthetic)" stroke="#16233f" dot={false} strokeWidth={1.5} />
        <Line type="monotone" dataKey="forecast" name="Forecast (mean)" stroke="#b8860f" dot={false} strokeWidth={2.25} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
