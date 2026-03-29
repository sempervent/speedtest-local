import { NavLink, Outlet } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  [
    "rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
    isActive ? "bg-ink-800 text-accent" : "text-slate-300 hover:bg-ink-800/80 hover:text-white",
  ].join(" ");

export function Layout() {
  return (
    <div className="min-h-dvh flex flex-col">
      <header className="border-b border-ink-700 bg-ink-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent/80">LAN / Wi‑Fi</p>
            <h1 className="text-xl font-semibold text-white">speedtest-local</h1>
            <p className="text-sm text-slate-400">Self-hosted throughput & latency lab</p>
          </div>
          <nav className="flex flex-wrap gap-1" aria-label="Primary">
            <NavLink to="/" className={linkClass} end>
              Run test
            </NavLink>
            <NavLink to="/history" className={linkClass}>
              History
            </NavLink>
            <NavLink to="/analytics" className={linkClass}>
              Analytics
            </NavLink>
            <NavLink to="/settings" className={linkClass}>
              Settings
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-ink-800 py-6 text-center text-xs text-slate-500">
        Browser estimates only — see docs for methodology and limits.
      </footer>
    </div>
  );
}
