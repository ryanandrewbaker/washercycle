"""Tests for storage models."""

from __future__ import annotations

from custom_components.washercycle.models import CycleRecord, InternalState, TrainingRun


def test_cycle_roundtrip():
    cycle = CycleRecord(cycle_id="test-1", internal_state=InternalState.RUNNING)
    data = cycle.to_dict()
    restored = CycleRecord.from_dict(data)
    assert restored.cycle_id == "test-1"
    assert restored.internal_state == InternalState.RUNNING


def test_training_run_roundtrip():
    run = TrainingRun(
        run_id="r1",
        program_id="daily_wash",
        program_name="Daily Wash",
        user_start_at="2026-01-01T10:00:00+00:00",
        user_complete_at="2026-01-01T11:00:00+00:00",
        observed_duration_seconds=3600,
    )
    data = run.to_dict()
    restored = TrainingRun.from_dict(data)
    assert restored.run_id == "r1"
