export default function PageHeader({
  section,
  title,
  subtitle,
  badge,
}: {
  section: string;
  title: string;
  subtitle?: string;
  badge?: string;
}) {
  return (
    <div className="mb-6 flex items-start justify-between">
      <div>
        <p className="mb-1 text-xs text-ink-400">
          O2C AI <span className="mx-1">›</span> {section}
        </p>
        <h1 className="text-2xl font-semibold text-ink-700">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-500">{subtitle}</p>}
      </div>
      {badge && (
        <span className="rounded-full border border-gold-100 bg-gold-50 px-3 py-1 text-xs font-medium text-gold-600">
          {badge}
        </span>
      )}
    </div>
  );
}
