"""Calibration selector workflow tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.washercycle.cycle_archive import CycleArchive
from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import InternalState, SampleSource


def test_selector_label_consumed_at_start_not_reset_at_completion(detector_config):
    det = CycleDetector(config=detector_config, pending_program="daily_wash")
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    for i in range(6):
        det.process(
            DetectorInput(
                timestamp=base + timedelta(seconds=i * 5),
                power_w=50.0,
                door_open=False,
                power_available=True,
                source=SampleSource.POWER,
            )
        )
    assert det.cycle.calibration_program_id == "daily_wash"
    assert det.cycle.calibration_label_consumed is True
    assert det.pending_program == "daily_wash"


def test_archive_resets_pending_after_finalize(detector_config):
    archive = CycleArchive(post_completion_seconds=30)
    det = CycleDetector(config=detector_config, pending_program="bedding")
    det.cycle.internal_state = InternalState.NEEDS_EMPTYING
    det.cycle.started_at = "2026-07-31T09:00:00+00:00"
    det.cycle.completed_at = "2026-07-31T11:00:00+00:00"
    det.cycle.calibration_program_id = "bedding"
    det.cycle.calibration_label_consumed = True
    det.cycle.trace_compact = [
        {"timestamp": "2026-07-31T09:00:00+00:00", "power_w": 50.0},
        {"timestamp": "2026-07-31T11:00:00+00:00", "power_w": 3.0},
    ]
    archive.begin_post_window(det.cycle)
    run = archive.finalize(det.cycle)
    assert run.program_id == "bedding"
