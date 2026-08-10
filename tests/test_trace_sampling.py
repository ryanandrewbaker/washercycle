"""Trace sampling rules tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import InternalState, SampleSource


def _inp(ts: datetime, **kwargs) -> DetectorInput:
    source = kwargs.pop("source", SampleSource.POWER)
    return DetectorInput(timestamp=ts, source=source, **kwargs)


def test_tick_does_not_append_power_samples(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    det.cycle.trace_compact = [{"timestamp": base.isoformat(), "power_w": 50.0}]
    det.tick(base + timedelta(seconds=30))
    assert len(det.cycle.trace_compact) == 1


def test_door_update_without_power_change_does_not_duplicate_sample(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    det.process(_inp(base, power_w=50.0, source=SampleSource.POWER))
    assert len(det.cycle.trace_compact) == 1
    det.process(_inp(base + timedelta(seconds=5), door_open=False, source=SampleSource.DOOR))
    assert len(det.cycle.trace_compact) == 1


def test_power_entity_appends_trace_sample(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    det.process(_inp(base, power_w=50.0, source=SampleSource.POWER))
    det.process(_inp(base + timedelta(seconds=30), power_w=80.0, source=SampleSource.POWER))
    assert len(det.cycle.trace_compact) == 2
