"""Accuracy and latency metrics for WasherCycle diagnostics and replay."""

from __future__ import annotations

from typing import Any

from .resample import parse_ts, reporting_gap_stats, trace_to_power_samples


def compute_cycle_metrics(
    *,
    cycle_id: str,
    started_at: str | None,
    completed_at: str | None,
    detected_at: str | None,
    expected_completion_at: str | None,
    program_id: str | None,
    program_confidence: float,
    program_identified_at: str | None,
    completion_reason: str,
    match_rejection_reason: str | None,
    trace: list[dict[str, Any]],
    prediction_timeline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a metrics report for diagnostics or replay output."""
    metrics: dict[str, Any] = {
        "cycle_id": cycle_id,
        "program_id": program_id,
        "program_confidence": program_confidence,
        "completion_reason": completion_reason,
        "match_rejection_reason": match_rejection_reason,
        "prediction_timeline": prediction_timeline or [],
    }

    power_samples = trace_to_power_samples(trace)
    metrics["reporting_gaps"] = reporting_gap_stats([{"t": s["t"]} for s in power_samples])

    if started_at and program_identified_at:
        metrics["identification_elapsed_seconds"] = (
            parse_ts(program_identified_at) - parse_ts(started_at)
        ).total_seconds()

    if started_at and completed_at and expected_completion_at:
        actual = parse_ts(completed_at)
        predicted = parse_ts(expected_completion_at)
        metrics["eta_absolute_error_seconds"] = abs((predicted - actual).total_seconds())
        metrics["predicted_completion_at"] = expected_completion_at
        metrics["actual_backdated_completion_at"] = completed_at

    if completed_at and detected_at:
        metrics["completion_detection_latency_seconds"] = (
            parse_ts(detected_at) - parse_ts(completed_at)
        ).total_seconds()

    return metrics
