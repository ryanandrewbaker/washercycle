"""Completion detection tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.washercycle.completion import assess_completion
from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import InternalState, SampleSource


def test_conservative_completion_backdated_to_first_standby_sample(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = (base - timedelta(hours=2)).isoformat()
    standby_start = base
    det.cycle.standby_since = standby_start.isoformat()
    assessment = assess_completion(
        now=base + timedelta(seconds=120),
        started_at=det.cycle.started_at,
        standby_since=det.cycle.standby_since,
        current_power_w=2.0,
        elapsed_seconds=7200,
        energy_wh=400,
        trace=[],
        profile=None,
        config=detector_config,
        standby_confirm_seconds=60,
    )
    assert assessment.confirmed
    assert assessment.backdated_completed_at == standby_start


def test_completion_event_before_post_window_finalize(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    det.cycle.internal_state = InternalState.RUNNING
    det.cycle.started_at = (base - timedelta(hours=2)).isoformat()
    det.cycle.standby_since = (base - timedelta(seconds=90)).isoformat()
    events = []
    det._complete_cycle(base, "standby_bootstrap", events, backdated=base - timedelta(seconds=90))
    assert any(e.name == "washercycle_cycle_completed" for e in events)
    assert det.cycle.archive_pending is True
    assert det.cycle.post_window_until is not None
