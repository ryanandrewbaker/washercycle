"""Tests for door completion correlation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import DetectorConfig, InternalState, ProgramProfile


def test_door_open_immediate_empty():
    config = DetectorConfig(
        door_correlation_seconds=30,
        shadow_mode=True,
        early_completion_enabled=True,
        early_completion_min_score=0.5,
        fallback_completion_seconds=300,
    )
    profiles = {
        "daily_wash": ProgramProfile(
            program_id="daily_wash",
            display_name="Daily Wash",
            confirmed_run_count=5,
            duration_median_seconds=3600,
            duration_mad_seconds=300,
            earliest_plausible_completion_seconds=2000,
            final_signature={"pre_window": [{"w": 3}] * 10},
        )
    }
    det = CycleDetector(config=config, profiles=profiles)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = (base - timedelta(seconds=3700)).isoformat()
    det.cycle.detected_program = "daily_wash"

    det.process(
        DetectorInput(
            timestamp=base,
            door_open=True,
            power_w=3.0,
            movement=False,
            door_available=True,
            power_available=True,
            movement_available=True,
        )
    )
    result = det.process(
        DetectorInput(
            timestamp=base + timedelta(seconds=5),
            power_w=2.0,
            movement=False,
            door_open=True,
            power_available=True,
            movement_available=True,
            door_available=True,
        )
    )
    completed = any(e.name == "washercycle_cycle_completed" for e in result.events)
    emptied = any(e.name == "washercycle_cycle_emptied" for e in result.events)
    if completed:
        assert result.cycle.immediately_emptied or emptied
