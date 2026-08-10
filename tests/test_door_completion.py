"""Tests for door completion correlation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import DetectorConfig, InternalState, SampleSource


def test_door_open_during_needs_emptying_empties_cycle():
    config = DetectorConfig(door_correlation_seconds=30, shadow_mode=True)
    det = CycleDetector(config=config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.cycle.internal_state = InternalState.NEEDS_EMPTYING
    det.cycle.completed_at = (base - timedelta(minutes=5)).isoformat()
    result = det.process(
        DetectorInput(
            timestamp=base,
            door_open=True,
            door_available=True,
            source=SampleSource.DOOR,
        )
    )
    assert result.cycle.internal_state == InternalState.IDLE
    assert any(e.name == "washercycle_cycle_emptied" for e in result.events)
