"""Completion detection for WasherCycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import DetectorConfig, ProgramProfile
from .resample import parse_ts, prefix_mae_aligned, resample_trace, trace_to_power_samples


@dataclass
class CompletionAssessment:
    """Result of evaluating whether a cycle has completed."""

    confirmed: bool = False
    backdated_completed_at: datetime | None = None
    reason: str = ""
    signature_score: float = 0.0


def _standby_duration_seconds(standby_since: str | None, now: datetime) -> float:
    if not standby_since:
        return 0.0
    return (now - parse_ts(standby_since)).total_seconds()


def assess_completion(
    *,
    now: datetime,
    started_at: str,
    standby_since: str | None,
    current_power_w: float | None,
    elapsed_seconds: float,
    energy_wh: float,
    trace: list[dict[str, Any]],
    profile: ProgramProfile | None,
    config: DetectorConfig,
    standby_confirm_seconds: float = 60.0,
) -> CompletionAssessment:
    """Evaluate standby-based completion with optional learned signature."""
    result = CompletionAssessment()
    if current_power_w is not None and current_power_w >= config.standby_power_w:
        return result

    standby_elapsed = _standby_duration_seconds(standby_since, now)
    if standby_elapsed < standby_confirm_seconds:
        return result

    min_duration = config.provisional_min_duration_seconds
    if profile and profile.duration_median_seconds > 0:
        min_duration = min(
            min_duration,
            profile.earliest_plausible_completion_seconds or profile.duration_median_seconds * 0.6,
        )
    if elapsed_seconds < min_duration:
        return result

    if standby_since:
        result.backdated_completed_at = parse_ts(standby_since)
    else:
        result.backdated_completed_at = now

    signature = profile.final_signature if profile else {}
    pre_window = signature.get("pre_window", [])
    if pre_window and trace:
        origin = parse_ts(started_at)
        live_resampled = resample_trace(
            trace_to_power_samples(trace),
            origin=origin,
            interval_s=config.resample_interval_seconds,
        )
        ref_resampled = [
            {"offset_s": p.get("offset_s", i * config.resample_interval_seconds), "w": p["w"]}
            for i, p in enumerate(pre_window)
        ]
        mae = prefix_mae_aligned(live_resampled, ref_resampled)
        result.signature_score = max(0.0, 1.0 - mae)
        if result.signature_score >= 0.6:
            result.confirmed = True
            result.reason = "standby_signature"
            return result

    result.confirmed = True
    result.reason = "standby_bootstrap"
    return result
