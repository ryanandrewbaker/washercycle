"""Event idempotency across restart tests."""

from __future__ import annotations

from datetime import datetime, timedelta

from custom_components.washercycle.const import (
    EVENT_CYCLE_COMPLETED,
    EVENT_CYCLE_EMPTIED,
    EVENT_NEEDS_REWASH,
    EVENT_PROGRAM_IDENTIFIED,
)
from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import InternalState, SampleSource


def _inp(ts: datetime, **kwargs) -> DetectorInput:
    return DetectorInput(timestamp=ts, source=SampleSource.POWER, **kwargs)


def _running_detector(detector_config, base):
    det = CycleDetector(config=detector_config)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    det.cycle.start_candidate_at = base.isoformat()
    det.cycle.events_emitted[EVENT_CYCLE_COMPLETED] = True
    return det


def test_restart_does_not_reemit_cycle_completed(detector_config, base_time):
    det = _running_detector(detector_config, base_time)
    result = det.tick(base_time + timedelta(minutes=60))
    completed = [e for e in result.events if e.name == EVENT_CYCLE_COMPLETED]
    assert completed == []


def test_restart_does_not_reemit_program_identified(detector_config, base_time):
    det = CycleDetector(config=detector_config)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base_time.isoformat()
    det.cycle.events_emitted[EVENT_PROGRAM_IDENTIFIED] = True
    det.cycle.detected_program = "daily_wash"
    result = det.process(_inp(base_time + timedelta(minutes=20), power_w=100.0))
    identified = [e for e in result.events if e.name == EVENT_PROGRAM_IDENTIFIED]
    assert identified == []


def test_restart_does_not_reemit_needs_rewash(detector_config, base_time):
    det = CycleDetector(config=detector_config)
    det.cycle.internal_state = InternalState.NEEDS_EMPTYING
    det.cycle.rewash_due_at = (base_time - timedelta(minutes=1)).isoformat()
    det.cycle.events_emitted[EVENT_NEEDS_REWASH] = True
    result = det.tick(base_time)
    rewash = [e for e in result.events if e.name == EVENT_NEEDS_REWASH]
    assert rewash == []


def test_restart_does_not_reemit_cycle_emptied(detector_config, base_time):
    det = CycleDetector(config=detector_config)
    det.cycle.internal_state = InternalState.NEEDS_EMPTYING
    det.cycle.events_emitted[EVENT_CYCLE_EMPTIED] = True
    result = det.process(
        DetectorInput(
            timestamp=base_time,
            door_open=True,
            door_available=True,
            source=SampleSource.DOOR,
        )
    )
    emptied = [e for e in result.events if e.name == EVENT_CYCLE_EMPTIED]
    assert emptied == []
