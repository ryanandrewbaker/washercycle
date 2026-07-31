"""Tests for restart recovery."""

from __future__ import annotations

from custom_components.washercycle.detector import CycleDetector
from custom_components.washercycle.models import CycleRecord, DetectorConfig, InternalState


def test_restart_does_not_reemit_start():
    config = DetectorConfig(shadow_mode=True)
    cycle = CycleRecord(
        cycle_id="existing",
        internal_state=InternalState.RUNNING,
        started_at="2026-07-31T10:00:00+00:00",
        events_emitted={"washercycle_cycle_started": True},
    )
    det = CycleDetector(config=config, cycle=cycle)
    det.restore(cycle)
    assert det.cycle.restart_recovered is True
    assert det.cycle.events_emitted.get("washercycle_cycle_started") is True


def test_restore_needs_emptying_timers():
    config = DetectorConfig(rewash_delay_minutes=120)
    cycle = CycleRecord(
        cycle_id="existing",
        internal_state=InternalState.NEEDS_EMPTYING,
        needs_emptying_at="2026-07-31T10:00:00+00:00",
        rewash_due_at="2026-07-31T12:00:00+00:00",
    )
    det = CycleDetector(config=config, cycle=cycle)
    det.restore(cycle)
    assert det.cycle.rewash_due_at is not None
