"""Tick and timer tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.washercycle.detector import CycleDetector
from custom_components.washercycle.models import InternalState


def test_rewash_fires_on_tick_without_source_update(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    det.cycle.internal_state = InternalState.NEEDS_EMPTYING
    det.cycle.rewash_due_at = (base + timedelta(minutes=1)).isoformat()
    result = det.tick(base + timedelta(minutes=2))
    assert result.cycle.internal_state == InternalState.NEEDS_REWASH
    assert any(e.name == "washercycle_needs_rewash" for e in result.events)


def test_progress_updates_on_tick(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = base.isoformat()
    det.cycle.progress = 0.0
    result = det.tick(base + timedelta(minutes=30))
    assert result.cycle.progress >= 0
