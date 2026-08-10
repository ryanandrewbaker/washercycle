"""Tests for cycle detector."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import InternalState, SampleSource


def _inp(ts: datetime, **kwargs) -> DetectorInput:
    kwargs.setdefault("source", SampleSource.POWER)
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
    first_candidate = None
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
        if result.cycle.start_candidate_at and first_candidate is None:
            first_candidate = result.cycle.start_candidate_at
        all_events.extend(result.events)
    assert result.cycle.internal_state == InternalState.RUNNING
    assert result.cycle.started_at == first_candidate
    assert any(e.name == "washercycle_cycle_started" for e in all_events)


def test_started_at_is_first_qualifying_transition_not_confirmation(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.process(_inp(base, power_w=50.0, door_open=False, power_available=True))
    assert det.cycle.start_candidate_at == base.isoformat()
    confirm_time = base + timedelta(seconds=30)
    det.process(_inp(confirm_time, power_w=50.0, door_open=False, power_available=True))
    assert det.cycle.started_at == base.isoformat()
    assert det.cycle.started_at != confirm_time.isoformat()


def test_door_open_alone_does_not_complete(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    result = det.process(
        DetectorInput(
            timestamp=base + timedelta(seconds=60),
            door_open=True,
            door_available=True,
            source=SampleSource.DOOR,
        )
    )
    assert result.cycle.internal_state == InternalState.RUNNING


def test_no_duplicate_start_event(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    det.cycle.events_emitted["washercycle_cycle_started"] = True
    result = det.process(_inp(base + timedelta(seconds=10), power_w=50.0))
    assert not any(e.name == "washercycle_cycle_started" for e in result.events)
