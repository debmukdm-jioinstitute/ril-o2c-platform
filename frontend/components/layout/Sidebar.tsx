"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { label: "Market Forecasting", href: "/", icon: "chart" },
  { label: "Scenario Analysis", href: "/scenario-analysis", icon: "scenario" },
  { label: "Price Intelligence", href: "/price-intelligence", icon: "price" },
  { label: "Supply & Demand", href: "/supply-demand", icon: "network" },
  { label: "Model Library", href: "/model-library", icon: "library" },
  { label: "Reports", href: "/reports", icon: "report" },
] as const;

const UTILITY_ITEMS = [
  { label: "Data Management", href: "/data-management", icon: "database" },
  { label: "Settings", href: "/settings", icon: "settings" },
] as const;

function NavIcon({ name }: { name: string }) {
  const common = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  switch (name) {
    case "chart":
      return <svg {...common}><path d="M4 19V9m6 10V5m6 14v-7" /></svg>;
    case "scenario":
      return <svg {...common}><path d="M3 17l4-6 4 3 6-9 4 5" /></svg>;
    case "price":
      return <svg {...common}><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" /></svg>;
    case "network":
      return <svg {...common}><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="12" cy="18" r="2.5" /><path d="M8 7l7 0M7.5 8.3L11 16M16.5 8.3L13 16" /></svg>;
    case "library":
      return <svg {...common}><path d="M4 4h4v16H4zM10 4h4v16h-4zM16 6l4-1.2V19l-4 1.2z" /></svg>;
    case "report":
      return <svg {...common}><path d="M6 3h9l3 3v15H6z" /><path d="M15 3v3h3M9 12h6M9 16h6M9 8h3" /></svg>;
    case "database":
      return <svg {...common}><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></svg>;
    case "settings":
      return <svg {...common}><circle cx="12" cy="12" r="3" /><path d="M19.4 13.5a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.9 2.9l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V20a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.9-2.9l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H4a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.9-2.9l.1.1a1.7 1.7 0 0 0 1.9.3H10a1.7 1.7 0 0 0 1-1.5V4a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.9 2.9l-.1.1a1.7 1.7 0 0 0-.3 1.9V10c.1.7.6 1.3 1.5 1.5h.1a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" /></svg>;
    default:
      return null;
  }
}

function NavLink({ item, active }: { item: { label: string; href: string; icon: string }; active: boolean }) {
  return (
    <Link
      href={item.href}
      className={
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors " +
        (active
          ? "bg-gold-50 font-medium text-gold-600"
          : "text-ink-500 hover:bg-cream-200 hover:text-ink-700")
      }
    >
      <NavIcon name={item.icon} />
      {item.label}
    </Link>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col justify-between border-r border-line bg-white px-4 py-6">
      <div>
        <div className="mb-8 px-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-gold-600">O2C AI</p>
          <p className="text-sm text-ink-500">Decision Intelligence</p>
        </div>
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.href} item={item} active={pathname === item.href} />
          ))}
        </nav>
        <div className="my-4 border-t border-line" />
        <nav className="space-y-1">
          {UTILITY_ITEMS.map((item) => (
            <NavLink key={item.href} item={item} active={pathname === item.href} />
          ))}
        </nav>
      </div>

      <div className="rounded-lg border border-line bg-cream-100 p-4 text-xs text-ink-500">
        <p className="font-medium text-ink-700">People. Ideas. Outcomes.</p>
        <p className="mt-1">
          Research prototype — synthetic data unless a live source is explicitly wired in.
          Complements the existing LP optimizer.
        </p>
      </div>
    </aside>
  );
}
