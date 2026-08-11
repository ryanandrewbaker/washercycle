"""Cycle isolation tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.washercycle.detector import CycleDetector, DetectorInput
from custom_components.washercycle.models import InternalState, SampleSource


def _start_cycle(det: CycleDetector, base: datetime, *, energy_offset: float = 100.0) -> str:
    for i in range(6):
        det.process(
            DetectorInput(
                timestamp=base + timedelta(seconds=i * 5),
                power_w=50.0,
                energy_wh=energy_offset + i,
                door_open=False,
                power_available=True,
                energy_available=True,
                source=SampleSource.POWER,
            )
        )
    assert det.cycle.internal_state == InternalState.RUNNING
    return det.cycle.cycle_id


def test_sequential_cycles_get_fresh_state(detector_config):
    det = CycleDetector(config=detector_config)
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)

    first_id = _start_cycle(det, base)
    first_trace_len = len(det.cycle.trace_compact)

    det.cycle.internal_state = InternalState.IDLE
    det.cycle.trace_compact = [{"timestamp": base.isoformat(), "power_w": 99.0}]
    det.cycle.accumulated_energy_wh = 42.0
    det.cycle.energy_at_start_wh = 999.0

    second_base = base + timedelta(hours=2)
    second_id = _start_cycle(det, second_base, energy_offset=200.0)

    assert second_id != first_id
    assert det.cycle.energy_at_start_wh == 200.0
    assert det.cycle.accumulated_energy_wh == 5.0
    assert det.cycle.trace_compact[0]["timestamp"] == second_base.isoformat()
    assert first_trace_len > 0
