"""Time-aligned trace resampling for WasherCycle."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_ts(ts: str | datetime) -> datetime:
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def trace_to_power_samples(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract power samples from compact trace or raw power list."""
    if not trace:
        return []
    if "t" in trace[0]:
        return trace
    return [
        {"t": p["timestamp"], "w": p.get("power_w", p.get("w", 0))}
        for p in trace
        if p.get("power_w") is not None or p.get("w") is not None
    ]


def reporting_gap_stats(samples: list[dict[str, Any]], *, ts_key: str = "t") -> dict[str, float]:
    """Compute inter-sample gap statistics in seconds."""
    if len(samples) < 2:
        return {"p50": 0.0, "p95": 0.0, "max": 0.0}
    gaps: list[float] = []
    for i in range(1, len(samples)):
        a = parse_ts(samples[i - 1][ts_key]).timestamp()
        b = parse_ts(samples[i][ts_key]).timestamp()
        gaps.append(max(0.0, b - a))
    gaps.sort()
    n = len(gaps)

    def _pct(p: float) -> float:
        return gaps[min(n - 1, int(n * p))]

    return {"p50": _pct(0.5), "p95": _pct(0.95), "max": gaps[-1]}


def resample_trace(
    samples: list[dict[str, Any]],
    *,
    origin: datetime,
    interval_s: int = 15,
    end_offset_s: float | None = None,
) -> list[dict[str, Any]]:
    """Resample irregular power samples onto a fixed elapsed-time grid.

    Uses hold-last-value. Does not insert duplicate samples for missing reports.
    """
    if not samples:
        return []
    keyed = []
    for s in samples:
        ts = parse_ts(s.get("t", s.get("timestamp")))
        w = s.get("w", s.get("power_w", 0))
        keyed.append((ts, float(w or 0)))
    keyed.sort(key=lambda x: x[0])
    last_ts = keyed[-1][0]
    duration = (last_ts - origin).total_seconds()
    if end_offset_s is not None:
        duration = min(duration, end_offset_s)
    if duration < 0:
        return [{"offset_s": 0.0, "w": keyed[0][1]}]

    result: list[dict[str, Any]] = []
    idx = 0
    offset = 0.0
    while offset <= duration:
        target = origin.timestamp() + offset
        while idx < len(keyed) - 1 and keyed[idx + 1][0].timestamp() <= target:
            idx += 1
        result.append({"offset_s": offset, "w": keyed[idx][1]})
        offset += interval_s
    return result


def prefix_mae_aligned(
    live: list[dict[str, Any]],
    reference: list[dict[str, Any]],
    *,
    max_offset_s: float | None = None,
) -> float:
    """Normalized MAE comparing resampled traces by elapsed offset_s."""
    if not live or not reference:
        return 1.0
    ref_by_offset = {r["offset_s"]: r["w"] for r in reference}
    diffs: list[float] = []
    for point in live:
        offset = point["offset_s"]
        if max_offset_s is not None and offset > max_offset_s:
            break
        if offset not in ref_by_offset:
            continue
        a = point["w"]
        b = ref_by_offset[offset]
        max_val = max(abs(a), abs(b), 1.0)
        diffs.append(abs(a - b) / max_val)
    if not diffs:
        return 1.0
    return sum(diffs) / len(diffs)


def _extract_final_signature_impl(
    power_samples: list[dict[str, Any]],
    complete_at: str,
    pre_seconds: int,
    post_seconds: int,
) -> dict[str, Any]:
    """Extract final signature window around completion."""
    complete_ts = parse_ts(complete_at).timestamp()
    pre_start = complete_ts - pre_seconds
    post_end = complete_ts + post_seconds
    pre_window = []
    post_window = []
    for s in power_samples:
        ts = parse_ts(s.get("t", s.get("timestamp"))).timestamp()
        if pre_start <= ts <= complete_ts:
            pre_window.append({"offset_s": ts - complete_ts, "w": s.get("w", 0)})
        elif complete_ts < ts <= post_end:
            post_window.append({"offset_s": ts - complete_ts, "w": s.get("w", 0)})
    return {"pre_window": pre_window, "post_window": post_window}
