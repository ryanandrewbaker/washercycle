"""Metrics reporting tests."""

from __future__ import annotations

from custom_components.washercycle.metrics import compute_cycle_metrics


def test_metrics_includes_required_fields():
    metrics = compute_cycle_metrics(
        cycle_id="abc",
        started_at="2026-07-31T10:00:00+00:00",
        completed_at="2026-07-31T12:00:00+00:00",
        detected_at="2026-07-31T12:01:00+00:00",
        expected_completion_at="2026-07-31T12:05:00+00:00",
        program_id="daily_wash",
        program_confidence=0.85,
        program_identified_at="2026-07-31T10:30:00+00:00",
        completion_reason="standby_bootstrap",
        match_rejection_reason=None,
        trace=[{"timestamp": "2026-07-31T10:00:00+00:00", "power_w": 50}],
    )
    assert "reporting_gaps" in metrics
    assert "completion_detection_latency_seconds" in metrics
    assert "eta_absolute_error_seconds" in metrics
    assert metrics["completion_reason"] == "standby_bootstrap"
