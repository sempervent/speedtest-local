export function GaugeTile({
  label,
  value,
  unit,
  sub,
}: {
  label: string;
  value: string;
  unit?: string;
  sub?: string;
}) {
  return (
    <div
      className="relative overflow-hidden rounded-2xl border border-ink-700 bg-gradient-to-br from-ink-900 to-ink-950 p-5 shadow-lg"
      role="status"
      aria-label={label}
    >
      <div className="pointer-events-none absolute -right-6 -top-10 h-32 w-32 rounded-full bg-accent/10 blur-2xl" />
      <p className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-2 font-mono text-3xl font-semibold text-white tabular-nums">
        {value}
        {unit ? <span className="ml-1 text-lg text-accent">{unit}</span> : null}
      </p>
      {sub ? <p className="mt-1 text-xs text-slate-500">{sub}</p> : null}
    </div>
  );
}
