"""Diagnostics tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.washercycle.diagnostics import async_get_diagnostics
from custom_components.washercycle.models import CycleRecord, InternalState, LatencyStats


@pytest.mark.asyncio
async def test_diagnostics_snapshot_excludes_removed_fields():
    cycle = CycleRecord(cycle_id="diag-1", internal_state=InternalState.IDLE)
    coordinator = MagicMock()
    coordinator.detector = MagicMock(cycle=cycle)
    coordinator.storage = MagicMock()
    coordinator.storage.get_profiles.return_value = {}
    coordinator.storage.get_training_runs.return_value = []
    coordinator.storage.get_latency_stats.return_value = LatencyStats()
    coordinator.storage.get_data_quality_counters.return_value = {}
    coordinator.storage.get_transitions.return_value = []
    coordinator.storage.get_pending_program.return_value = "auto"
    coordinator.data = {"last_cycle_summary": {}}
    coordinator.normalizer = MagicMock(state=MagicMock(rejected=[]))

    entry = MagicMock()
    entry.version = 1
    entry.data = {"power_sensor": "sensor.power"}
    entry.options = {"shadow_mode": True}

    hass = MagicMock()
    hass.data = {"washercycle": {"entry-1": coordinator}}

    result = await async_get_diagnostics(hass, entry)

    assert "detector_state" in result
    assert "pending_program" in result
    assert "profile_summary" in result
    assert "recorder" not in result
    assert "announcement_state" not in result
