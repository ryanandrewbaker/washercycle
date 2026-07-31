"""Robust statistics helpers for WasherCycle profiles."""

from __future__ import annotations


def median(values: list[float]) -> float:
    """Compute median of values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def mad(values: list[float], med: float | None = None) -> float:
    """Median absolute deviation."""
    if not values:
        return 0.0
    m = med if med is not None else median(values)
    deviations = [abs(v - m) for v in values]
    return median(deviations)


def percentile(values: list[float], p: float) -> float:
    """Compute percentile (0-100)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def z_score_mad(value: float, med: float, mad_val: float) -> float:
    """Robust z-score using MAD."""
    if mad_val < 0.001:
        return 0.0 if abs(value - med) < 0.001 else 1.0
    return abs(value - med) / (1.4826 * mad_val)
