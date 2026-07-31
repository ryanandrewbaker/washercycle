"""Completion evidence scoring for WasherCycle."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import DetectorConfig, EvidenceScore, ProgramProfile
from .stats import z_score_mad


def _parse_ts(ts: str | datetime) -> datetime:
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _mean_abs_diff(trace_a: list[dict[str, Any]], trace_b: list[dict[str, Any]]) -> float:
    """Mean absolute difference between two power traces."""
    if not trace_a or not trace_b:
        return 1.0
    n = min(len(trace_a), len(trace_b))
    if n == 0:
        return 1.0
    diffs = []
    for i in range(n):
        a = trace_a[i].get("w", 0)
        b = trace_b[i].get("w", 0)
        max_val = max(abs(a), abs(b), 1.0)
        diffs.append(abs(a - b) / max_val)
    return sum(diffs) / len(diffs)


def _recent_power(trace: list[dict[str, Any]], seconds: int, now: datetime) -> list[float]:
    """Get power values from recent window."""
    cutoff = now.timestamp() - seconds
    return [
        p.get("power_w", 0)
        for p in trace
        if _parse_ts(p.get("timestamp", now.isoformat())).timestamp() >= cutoff
        and p.get("power_w") is not None
    ]


def score_completion_evidence(
    *,
    now: datetime,
    elapsed_seconds: float,
    current_power_w: float | None,
    movement_active: bool | None,
    energy_wh: float,
    energy_stable: bool,
    trace: list[dict[str, Any]],
    profile: ProgramProfile | None,
    config: DetectorConfig,
    movement_available: bool = True,
) -> EvidenceScore:
    """Compute weighted completion evidence score."""
    score = EvidenceScore()
    weights = {
        "power_signature_match": 0.35,
        "standby_power": 0.20,
        "movement_stopped": 0.15,
        "energy_stabilized": 0.10,
        "duration_plausible": 0.10,
        "transition_pattern": 0.10,
    }

    if not movement_available:
        extra = weights.pop("movement_stopped")
        weights["standby_power"] += extra * 0.5
        weights["power_signature_match"] += extra * 0.5

    standby_margin = 2.0
    learned_standby = profile.mean_power_median_w * 0.1 if profile and profile.mean_power_median_w else config.standby_power_w

    if current_power_w is not None:
        if current_power_w <= learned_standby + standby_margin:
            score.standby_power = 1.0
        elif current_power_w <= config.standby_power_w + standby_margin:
            score.standby_power = 0.7
        else:
            score.standby_power = 0.0
            if current_power_w >= config.start_power_w:
                score.contradictory = True
                score.reason = "power_resumed_above_start_threshold"

    if movement_active is not None:
        if not movement_active:
            score.movement_stopped = 1.0
        else:
            score.movement_stopped = 0.0
            if movement_available:
                score.contradictory = True
                score.reason = "movement_active"

    score.energy_stabilized = 1.0 if energy_stable else 0.3

    if profile and profile.duration_median_seconds > 0:
        dur_med = profile.duration_median_seconds
        dur_mad = profile.duration_mad_seconds or dur_med * 0.1
        z = z_score_mad(elapsed_seconds, dur_med, dur_mad)
        if z <= 2.0 and elapsed_seconds >= profile.earliest_plausible_completion_seconds:
            score.duration_plausible = max(0.0, 1.0 - z / 4.0)
        elif elapsed_seconds < profile.earliest_plausible_completion_seconds:
            score.duration_plausible = 0.0
        else:
            score.duration_plausible = 0.3
    elif elapsed_seconds >= config.provisional_min_duration_seconds:
        score.duration_plausible = 0.5
    else:
        score.duration_plausible = 0.0

    if profile and profile.final_signature.get("pre_window"):
        recent = _recent_power(trace, 300, now)
        if recent:
            live_trace = [{"w": w} for w in recent[-len(profile.final_signature["pre_window"]) :]]
            mae = _mean_abs_diff(live_trace, profile.final_signature["pre_window"])
            score.power_signature_match = max(0.0, 1.0 - mae)
            score.transition_pattern = score.power_signature_match * 0.8
    elif profile and profile.representative_trace:
        score.power_signature_match = 0.4
        score.transition_pattern = 0.3
    else:
        score.power_signature_match = 0.2 if score.standby_power > 0.5 else 0.0

    total = (
        score.power_signature_match * weights.get("power_signature_match", 0)
        + score.standby_power * weights.get("standby_power", 0)
        + score.movement_stopped * weights.get("movement_stopped", 0)
        + score.energy_stabilized * weights.get("energy_stabilized", 0)
        + score.duration_plausible * weights.get("duration_plausible", 0)
        + score.transition_pattern * weights.get("transition_pattern", 0)
    )
    score.total = min(1.0, total)
    return score


def correlated_door_completion_threshold() -> float:
    """Lower threshold for door-correlated completion."""
    return 0.6
