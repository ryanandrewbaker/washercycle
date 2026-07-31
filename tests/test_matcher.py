"""Tests for matcher."""

from __future__ import annotations

from custom_components.washercycle.matcher import match_program
from custom_components.washercycle.models import DetectorConfig, ProgramMatchState, ProgramProfile


def test_unknown_when_no_profiles():
    config = DetectorConfig(min_runs_recognition=3)
    pid, conf, state, _ = match_program(
        elapsed_seconds=600,
        energy_wh=100,
        trace=[],
        profiles={},
        config=config,
    )
    assert state == ProgramMatchState.UNKNOWN


def test_confident_match_with_margin():
    config = DetectorConfig(min_runs_recognition=1, matcher_margin=0.12)
    profiles = {
        "daily_wash": ProgramProfile(
            program_id="daily_wash",
            display_name="Daily Wash",
            confirmed_run_count=5,
            duration_median_seconds=3600,
            duration_mad_seconds=300,
            energy_median_wh=500,
            energy_mad_wh=50,
            earliest_identification_seconds=300,
            representative_trace=[{"w": 200}] * 20,
        ),
        "quick_wash": ProgramProfile(
            program_id="quick_wash",
            display_name="Quick Wash",
            confirmed_run_count=5,
            duration_median_seconds=1800,
            duration_mad_seconds=200,
            energy_median_wh=200,
            energy_mad_wh=30,
            earliest_identification_seconds=300,
            representative_trace=[{"w": 50}] * 20,
        ),
    }
    trace = [{"power_w": 200, "timestamp": "2026-01-01T10:00:00+00:00"}] * 20
    pid, conf, state, candidates = match_program(
        elapsed_seconds=1800,
        energy_wh=480,
        trace=trace,
        profiles=profiles,
        config=config,
    )
    assert pid == "daily_wash"
    assert state in (ProgramMatchState.CONFIDENT, ProgramMatchState.TENTATIVE)
