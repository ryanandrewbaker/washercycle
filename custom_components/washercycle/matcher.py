"""Live program matching for WasherCycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import DetectorConfig, ProgramCandidate, ProgramMatchState, ProgramProfile
from .preset import APPLIANCE_PRESET
from .resample import (
    parse_ts,
    prefix_mae_aligned,
    reporting_gap_stats,
    resample_trace,
    trace_to_power_samples,
)
from .stats import z_score_mad


@dataclass
class MatchResult:
    """Program match outcome with abstention metadata."""

    program_id: str | None
    confidence: float
    match_state: ProgramMatchState
    candidates: list[ProgramCandidate]
    rejection_reason: str | None = None
    emit_identified: bool = False


def match_program(
    *,
    started_at: str,
    now: datetime,
    elapsed_seconds: float,
    energy_wh: float,
    trace: list[dict[str, Any]],
    profiles: dict[str, ProgramProfile],
    config: DetectorConfig,
    manual_program: str | None = None,
    current_match: str | None = None,
    current_state: ProgramMatchState = ProgramMatchState.UNKNOWN,
    program_identified_emitted: bool = False,
) -> MatchResult:
    """Match live cycle to program profiles with abstention rules."""
    if manual_program and manual_program != "auto":
        return MatchResult(
            program_id=manual_program,
            confidence=1.0,
            match_state=ProgramMatchState.MANUAL,
            candidates=[],
            emit_identified=not program_identified_emitted,
        )

    power_samples = trace_to_power_samples(trace)
    gaps = reporting_gap_stats([{"t": s["t"]} for s in power_samples]) if power_samples else {
        "p50": 0.0,
        "p95": 0.0,
        "max": 0.0,
    }
    max_gap = float(APPLIANCE_PRESET["max_reporting_gap_p95_seconds"])
    if gaps["p95"] > max_gap:
        return MatchResult(
            program_id=current_match,
            confidence=0.0,
            match_state=ProgramMatchState.DETECTING,
            candidates=[],
            rejection_reason="reporting_gaps",
        )

    origin = parse_ts(started_at)
    live_resampled = resample_trace(
        power_samples,
        origin=origin,
        interval_s=config.resample_interval_seconds,
        end_offset_s=elapsed_seconds,
    )

    candidates: list[ProgramCandidate] = []
    min_real = int(APPLIANCE_PRESET["min_real_runs_recognition"])
    conf_threshold = float(APPLIANCE_PRESET["matcher_confidence_threshold"])
    margin_threshold = config.matcher_margin

    for pid, profile in profiles.items():
        if not profile.recognition_ready or profile.real_run_count < min_real:
            continue
        if profile.confirmed_run_count < config.min_runs_recognition:
            continue
        if elapsed_seconds < profile.earliest_identification_seconds:
            continue

        power_mae = 1.0
        if profile.representative_trace:
            power_mae = prefix_mae_aligned(live_resampled, profile.representative_trace)

        energy_z = 0.0
        if profile.energy_median_wh > 0:
            energy_z = z_score_mad(energy_wh, profile.energy_median_wh, profile.energy_mad_wh)

        power_score = max(0.0, 1.0 - power_mae)
        energy_score = max(0.0, 1.0 - min(energy_z, 3.0) / 3.0)
        duration_score = 0.5
        if profile.duration_median_seconds > 0:
            duration_z = z_score_mad(
                elapsed_seconds,
                profile.duration_median_seconds,
                profile.duration_mad_seconds,
            )
            duration_score = max(0.0, 1.0 - min(duration_z, 3.0) / 3.0)

        feature_score = 0.0
        if profile.feature_vector:
            fv = profile.feature_vector
            if fv.get("peak_power_w") and live_resampled:
                peak = max(p["w"] for p in live_resampled)
                peak_ref = fv["peak_power_w"]
                feature_score = max(0.0, 1.0 - abs(peak - peak_ref) / max(peak_ref, 1.0))

        score = (
            power_score * 0.45
            + energy_score * 0.20
            + duration_score * 0.20
            + feature_score * 0.15
        )
        candidates.append(
            ProgramCandidate(program_id=pid, score=score, energy_z=energy_z, power_mae=power_mae)
        )

    candidates.sort(key=lambda c: c.score, reverse=True)

    ready_profiles = [p for p in profiles.values() if p.recognition_ready and p.real_run_count >= min_real]
    if not ready_profiles:
        return MatchResult(
            program_id=None,
            confidence=0.0,
            match_state=ProgramMatchState.UNKNOWN,
            candidates=candidates,
            rejection_reason="insufficient_real_runs",
        )

    if not candidates:
        return MatchResult(
            program_id=None,
            confidence=0.0,
            match_state=ProgramMatchState.DETECTING,
            candidates=[],
            rejection_reason="insufficient_real_runs",
        )

    best = candidates[0]
    second_score = candidates[1].score if len(candidates) > 1 else 0.0
    margin = best.score - second_score

    hysteresis = float(APPLIANCE_PRESET["matcher_hysteresis_score"])
    if current_state == ProgramMatchState.CONFIDENT and current_match:
        if best.program_id == current_match and best.score >= hysteresis:
            return MatchResult(
                program_id=current_match,
                confidence=best.score,
                match_state=ProgramMatchState.CONFIDENT,
                candidates=candidates,
            )
        if best.program_id != current_match and best.score < conf_threshold:
            return MatchResult(
                program_id=current_match,
                confidence=best.score,
                match_state=ProgramMatchState.CONFIDENT,
                candidates=candidates,
            )

    if best.score < conf_threshold:
        return MatchResult(
            program_id=best.program_id,
            confidence=best.score,
            match_state=ProgramMatchState.DETECTING,
            candidates=candidates,
            rejection_reason="low_confidence",
        )

    if margin < margin_threshold:
        return MatchResult(
            program_id=best.program_id,
            confidence=best.score,
            match_state=ProgramMatchState.TENTATIVE,
            candidates=candidates,
            rejection_reason="narrow_margin",
        )

    emit = not program_identified_emitted
    return MatchResult(
        program_id=best.program_id,
        confidence=best.score,
        match_state=ProgramMatchState.CONFIDENT,
        candidates=candidates,
        emit_identified=emit,
    )
