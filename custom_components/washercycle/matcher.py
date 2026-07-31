"""Live program matching for WasherCycle."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import DetectorConfig, ProgramCandidate, ProgramMatchState, ProgramProfile
from .stats import z_score_mad


def _parse_ts(ts: str | datetime) -> datetime:
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _prefix_mae(live: list[dict[str, Any]], reference: list[dict[str, Any]]) -> float:
    """Mean absolute error between live and reference trace prefixes."""
    if not live or not reference:
        return 1.0
    n = min(len(live), len(reference))
    if n == 0:
        return 1.0
    diffs = []
    for i in range(n):
        a = live[i].get("power_w", live[i].get("w", 0)) or 0
        b = reference[i].get("w", 0)
        max_val = max(abs(a), abs(b), 1.0)
        diffs.append(abs(a - b) / max_val)
    return sum(diffs) / len(diffs)


def match_program(
    *,
    elapsed_seconds: float,
    energy_wh: float,
    trace: list[dict[str, Any]],
    profiles: dict[str, ProgramProfile],
    config: DetectorConfig,
    manual_program: str | None = None,
    current_match: str | None = None,
    current_state: ProgramMatchState = ProgramMatchState.UNKNOWN,
) -> tuple[str | None, float, ProgramMatchState, list[ProgramCandidate]]:
    """Match live cycle to program profiles."""
    if manual_program and manual_program != "auto":
        return manual_program, 1.0, ProgramMatchState.MANUAL, []

    candidates: list[ProgramCandidate] = []
    for pid, profile in profiles.items():
        if profile.confirmed_run_count < config.min_runs_recognition:
            continue
        if elapsed_seconds < profile.earliest_identification_seconds:
            continue

        power_mae = 1.0
        if profile.representative_trace:
            power_mae = _prefix_mae(trace, profile.representative_trace)

        energy_z = 0.0
        if profile.energy_median_wh > 0:
            energy_z = z_score_mad(energy_wh, profile.energy_median_wh, profile.energy_mad_wh)

        power_score = max(0.0, 1.0 - power_mae)
        energy_score = max(0.0, 1.0 - min(energy_z, 3.0) / 3.0)
        duration_score = 0.5
        if profile.duration_median_seconds > 0:
            duration_z = z_score_mad(
                elapsed_seconds, profile.duration_median_seconds, profile.duration_mad_seconds
            )
            duration_score = max(0.0, 1.0 - min(duration_z, 3.0) / 3.0)

        score = power_score * 0.5 + energy_score * 0.25 + duration_score * 0.25
        candidates.append(
            ProgramCandidate(program_id=pid, score=score, energy_z=energy_z, power_mae=power_mae)
        )

    candidates.sort(key=lambda c: c.score, reverse=True)

    if not candidates:
        eligible = [p for p in profiles.values() if p.confirmed_run_count >= 1]
        if not eligible:
            return None, 0.0, ProgramMatchState.UNKNOWN, []
        return None, 0.0, ProgramMatchState.DETECTING, candidates

    best = candidates[0]
    second_score = candidates[1].score if len(candidates) > 1 else 0.0
    margin = best.score - second_score

    if current_state == ProgramMatchState.CONFIDENT and current_match:
        if best.program_id == current_match and best.score >= 0.45:
            return current_match, best.score, ProgramMatchState.CONFIDENT, candidates
        if best.program_id != current_match and best.score < 0.55:
            return current_match, best.score, ProgramMatchState.CONFIDENT, candidates

    if best.score >= 0.70 and margin >= config.matcher_margin:
        return best.program_id, best.score, ProgramMatchState.CONFIDENT, candidates
    if best.score >= 0.55:
        return best.program_id, best.score, ProgramMatchState.TENTATIVE, candidates
    return best.program_id, best.score, ProgramMatchState.DETECTING, candidates
