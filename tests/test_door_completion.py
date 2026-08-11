"""Tests for door completion correlation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.washercycle.cycle_archive import CycleArchive
from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import DetectorConfig, InternalState, SampleSource


def test_door_open_during_needs_emptying_empties_cycle():
    config = DetectorConfig(door_correlation_seconds=30, shadow_mode=True)
    det = CycleDetector(config=config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
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


def test_immediate_door_emptying_archives_once_without_duplicate_events(detector_config):
    archive = CycleArchive(post_completion_seconds=30)
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    det.cycle.internal_state = InternalState.NEEDS_EMPTYING
    det.cycle.started_at = (base - timedelta(hours=1)).isoformat()
    det.cycle.completed_at = (base - timedelta(minutes=5)).isoformat()
    det.cycle.trace_compact = [
        {"timestamp": det.cycle.started_at, "power_w": 50.0},
        {"timestamp": det.cycle.completed_at, "power_w": 3.0},
    ]
    archive.begin_post_window(det.cycle)
    det.cycle.post_window_until = (base + timedelta(seconds=30)).isoformat()

    empty_result = det.process(
        DetectorInput(
            timestamp=base,
            door_open=True,
            door_available=True,
            source=SampleSource.DOOR,
        )
    )
    emptied_events = [e for e in empty_result.events if e.name == "washercycle_cycle_emptied"]
    assert len(emptied_events) == 1
    assert empty_result.cycle.internal_state == InternalState.IDLE

    tick_result = det.tick(base + timedelta(seconds=31))
    assert tick_result.finalize_archive is True
    run = archive.finalize(tick_result.cycle)
    assert run.run_id
    assert archive.is_pending(det.cycle.cycle_id) is False
