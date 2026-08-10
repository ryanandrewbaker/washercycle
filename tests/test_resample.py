"""Resampling tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.washercycle.resample import reporting_gap_stats, resample_trace


def test_irregular_reports_resampled_by_elapsed_time():
    origin = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    samples = [
        {"t": origin.isoformat(), "w": 10},
        {"t": (origin + timedelta(seconds=45)).isoformat(), "w": 100},
        {"t": (origin + timedelta(seconds=90)).isoformat(), "w": 200},
    ]
    resampled = resample_trace(samples, origin=origin, interval_s=15)
    assert resampled[0] == {"offset_s": 0.0, "w": 10}
    assert resampled[1]["w"] == 10
    assert resampled[3]["w"] == 100
    assert resampled[6]["w"] == 200


def test_gap_stats_on_irregular_trace():
    origin = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    samples = [
        {"t": origin.isoformat()},
        {"t": (origin + timedelta(seconds=10)).isoformat()},
        {"t": (origin + timedelta(seconds=200)).isoformat()},
    ]
    gaps = reporting_gap_stats(samples)
    assert gaps["max"] == 190.0
