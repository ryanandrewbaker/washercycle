"""Energy baseline tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import InternalState, SampleSource


def test_energy_baseline_set_from_power_source_at_start(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    for i in range(6):
        det.process(
            DetectorInput(
                timestamp=base + timedelta(seconds=i * 5),
                power_w=50.0,
                energy_wh=10.0 + i * 0.5,
                door_open=False,
                power_available=True,
                energy_available=True,
                source=SampleSource.POWER,
            )
        )
    assert det.cycle.energy_at_start_wh == 10.0
    assert det.cycle.accumulated_energy_wh == 2.5


def test_tick_confirmed_start_uses_passed_energy_baseline(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    det.cycle.internal_state = InternalState.START_CANDIDATE
    det.cycle.start_candidate_at = base.isoformat()
    det.cycle.cycle_id = "tick-start"

    result = det.tick(base + timedelta(seconds=30), energy_wh=25.0)

    assert result.cycle.internal_state == InternalState.RUNNING
    assert result.cycle.energy_at_start_wh == 25.0
