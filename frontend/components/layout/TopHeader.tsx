import Logo from "./Logo";

export default function TopHeader() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-line bg-white px-6">
      <div className="flex items-center gap-3">
        <Logo size={32} />
        <div className="leading-tight">
          <p className="text-sm font-semibold text-ink-700">O2C AI Decision Intelligence</p>
          <p className="text-[11px] text-ink-400">Petrochemical economics &amp; market forecasting</p>
        </div>
      </div>

      <div className="hidden flex-1 justify-center md:flex">
        <div className="relative w-full max-w-md">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400"
            width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          <input
            type="text"
            placeholder="Search datasets, models, reports…"
            className="w-full rounded-full border border-line bg-cream-100 py-2 pl-9 pr-4 text-sm text-ink-700 placeholder:text-ink-400 focus:border-gold-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
            disabled
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative text-ink-500 hover:text-ink-700" aria-label="Notifications" disabled>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.7 21a2 2 0 0 1-3.4 0" />
          </svg>
        </button>
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-xs font-semibold text-white">
            DM
          </div>
          <div className="hidden leading-tight sm:block">
            <p className="text-sm font-medium text-ink-700">Debabrata Mukherjee</p>
            <p className="text-[11px] text-ink-400">O2C Analytics</p>
          </div>
        </div>
      </div>
    </header>
  );
}
