"""Storage migration tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.washercycle.storage import WasherCycleStorage


def test_migrate_v1_to_v2_removes_announcement_state():
    hass = MagicMock()
    storage = WasherCycleStorage(hass, "test_entry")
    data = {
        "version": 1,
        "announcement_state": {"completion_sent": True},
        "training_runs": [{"run_id": "r1", "note": "manual timing"}],
        "profiles": {},
    }
    migrated = storage._migrate(data)
    assert migrated["version"] == 2
    assert "announcement_state" not in migrated
    assert "manual_timing" in migrated["training_runs"][0].get("anomaly_flags", [])
