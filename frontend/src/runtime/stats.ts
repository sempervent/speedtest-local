export function mean(xs: number[]): number {
  if (xs.length === 0) return 0;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

export function stddev(xs: number[]): number {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  const v = mean(xs.map((x) => (x - m) ** 2));
  return Math.sqrt(v);
}

/** Mean absolute successive difference — common jitter proxy for ping RTTs. */
export function successiveJitterMs(rttsMs: number[]): number {
  if (rttsMs.length < 2) return 0;
  let s = 0;
  for (let i = 1; i < rttsMs.length; i++) {
    s += Math.abs(rttsMs[i]! - rttsMs[i - 1]!);
  }
  return s / (rttsMs.length - 1);
}
