"""Tests for program matcher."""

from __future__ import annotations

from datetime import datetime, timezone

from custom_components.washercycle.matcher import match_program
from custom_components.washercycle.models import DetectorConfig, ProgramMatchState, ProgramProfile


def test_unknown_when_no_profiles():
    config = DetectorConfig()
    started = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    result = match_program(
        started_at=started.isoformat(),
        now=started,
        elapsed_seconds=600,
        energy_wh=100,
        trace=[],
        profiles={},
        config=config,
    )
    assert result.match_state == ProgramMatchState.UNKNOWN
    assert result.rejection_reason == "insufficient_real_runs"


def test_abstains_without_recognition_ready_profiles():
    config = DetectorConfig(min_runs_recognition=1)
    started = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    profiles = {
        "daily_wash": ProgramProfile(
            program_id="daily_wash",
            display_name="Daily Wash",
            confirmed_run_count=5,
            recognition_ready=False,
            real_run_count=0,
            duration_median_seconds=3600,
            duration_mad_seconds=300,
            energy_median_wh=400,
            representative_trace=[{"offset_s": 0, "w": 50}],
            earliest_identification_seconds=100,
        )
    }
    result = match_program(
        started_at=started.isoformat(),
        now=started,
        elapsed_seconds=1200,
        energy_wh=200,
        trace=[{"timestamp": started.isoformat(), "power_w": 50}],
        profiles=profiles,
        config=config,
    )
    assert result.rejection_reason == "insufficient_real_runs"
    assert result.emit_identified is False
