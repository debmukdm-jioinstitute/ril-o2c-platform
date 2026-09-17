export default function StatCard({
  label,
  value,
  unit,
  delta,
  deltaLabel,
  deltaDirection,
}: {
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  deltaLabel?: string;
  deltaDirection?: "up" | "down" | "neutral";
}) {
  const deltaColor =
    deltaDirection === "up" ? "text-emerald-600" : deltaDirection === "down" ? "text-rose-600" : "text-ink-400";
  return (
    <div className="rounded-xl border border-line bg-white p-4 shadow-card">
      <p className="text-xs font-medium text-ink-400">{label}</p>
      <p className="mt-1.5 text-xl font-semibold text-ink-700">
        {value}
        {unit && <span className="ml-1 text-sm font-normal text-ink-400">{unit}</span>}
      </p>
      {delta && (
        <p className={`mt-1 flex items-center gap-1 text-xs font-medium ${deltaColor}`}>
          {deltaDirection === "up" ? "▲" : deltaDirection === "down" ? "▼" : ""} {delta}
          {deltaLabel && <span className="font-normal text-ink-400">{deltaLabel}</span>}
        </p>
      )}
    </div>
  );
}
