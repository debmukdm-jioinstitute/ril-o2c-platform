"use client";

import { dataQualityLabel, type FeedstockComparisonRow } from "@/lib/api";

function fmt(n: number, digits = 0) {
  return n.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function QualityDot({ quality }: { quality: string | undefined }) {
  const label = dataQualityLabel(quality);
  const isLive = label === "Live Market Data";
  return (
    <span
      title={label}
      className={"ml-2 inline-block h-1.5 w-1.5 rounded-full align-middle " + (isLive ? "bg-emerald-500" : "bg-gold-400")}
    />
  );
}

export default function FeedstockTable({
  rows,
  qualityByFeedstock = {},
}: {
  rows: FeedstockComparisonRow[];
  qualityByFeedstock?: Record<string, string>;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-white shadow-card">
      <table className="w-full text-sm">
        <thead className="bg-cream-100 text-ink-400">
          <tr>
            <th className="px-4 py-3 text-left font-medium">Rank</th>
            <th className="px-4 py-3 text-left font-medium">Feedstock</th>
            <th className="px-4 py-3 text-right font-medium">Ethylene t/d</th>
            <th className="px-4 py-3 text-right font-medium">Revenue $/d</th>
            <th className="px-4 py-3 text-right font-medium">CM $/t ethylene</th>
            <th className="px-4 py-3 text-right font-medium">EBITDA ₹cr/yr</th>
            <th className="px-4 py-3 text-right font-medium">Margin %</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.scenario} className="border-t border-line hover:bg-cream-100/60">
              <td className="px-4 py-3 text-ink-400">#{r.rank}</td>
              <td className="px-4 py-3 font-medium capitalize text-ink-700">
                {r.feedstock}
                <QualityDot quality={qualityByFeedstock[r.feedstock]} />
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-ink-600">{fmt(r.ethylene_tons_day, 1)}</td>
              <td className="px-4 py-3 text-right tabular-nums text-ink-600">{fmt(r.revenue_usd_day)}</td>
              <td
                className={`px-4 py-3 text-right tabular-nums font-medium ${
                  r.cm_usd_per_ton_ethylene >= 0 ? "text-emerald-600" : "text-rose-600"
                }`}
              >
                {fmt(r.cm_usd_per_ton_ethylene, 1)}
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-ink-600">{fmt(r.ebitda_inr_cr_year, 1)}</td>
              <td className="px-4 py-3 text-right tabular-nums text-ink-600">{fmt(r.margin_pct_of_revenue, 2)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
