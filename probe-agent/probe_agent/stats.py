"""Aligned with docs/measurement-methodology.md (browser-equivalent summaries)."""

from __future__ import annotations


def mean(xs: list[float]) -> float:
    if not xs:
        return 0.0
    return sum(xs) / len(xs)


def stddev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5


def successive_jitter_ms(rtts_ms: list[float]) -> float:
    if len(rtts_ms) < 2:
        return 0.0
    s = 0.0
    for i in range(1, len(rtts_ms)):
        s += abs(rtts_ms[i] - rtts_ms[i - 1])
    return s / (len(rtts_ms) - 1)
