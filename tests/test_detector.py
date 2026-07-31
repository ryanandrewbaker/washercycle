"""Tests for cycle detector."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import InternalState


def _inp(ts: datetime, **kwargs) -> DetectorInput:
    return DetectorInput(timestamp=ts, **kwargs)


def test_brief_power_spike_does_not_start_cycle(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.process(_inp(base, power_w=25.0, door_open=False, power_available=True))
    result = det.process(
        _inp(base + timedelta(seconds=2), power_w=3.0, door_open=False, power_available=True)
    )
    assert result.cycle.internal_state == InternalState.IDLE


def test_genuine_start_after_sustain(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    all_events = []
    for i in range(6):
        result = det.process(
            _inp(
                base + timedelta(seconds=i * 5),
                power_w=50.0,
                energy_wh=100.0 + i,
                door_open=False,
                power_available=True,
                energy_available=True,
            )
        )
        all_events.extend(result.events)
    assert result.cycle.internal_state == InternalState.RUNNING
    assert any(e.name == "washercycle_cycle_started" for e in all_events)


def test_door_open_alone_does_not_complete(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    result = det.process(_inp(base + timedelta(seconds=60), door_open=True, door_available=True))
    assert result.cycle.internal_state == InternalState.RUNNING


def test_fallback_completion(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    det.cycle.standby_since = (base + timedelta(seconds=10)).isoformat()
    result = det.process(
        _inp(
            base + timedelta(seconds=80),
            power_w=2.0,
            movement=False,
            power_available=True,
            movement_available=True,
        )
    )
    assert result.cycle.internal_state in (
        InternalState.NEEDS_EMPTYING,
        InternalState.END_CANDIDATE,
    )


def test_no_duplicate_start_event(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    det.cycle.events_emitted["washercycle_cycle_started"] = True
    result = det.process(_inp(base + timedelta(seconds=30), power_w=50.0, power_available=True))
    assert not any(e.name == "washercycle_cycle_started" for e in result.events)
