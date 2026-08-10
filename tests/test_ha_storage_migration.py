"""Home Assistant Store envelope migration tests."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.washercycle.const import STORAGE_KEY, STORAGE_VERSION
from custom_components.washercycle.storage import WasherCycleStorage
from tests.helpers.v1_storage import sample_v1_storage_payload


from tests.helpers.ha_installed import home_assistant_installed

pytestmark = pytest.mark.skipif(
    not home_assistant_installed(),
    reason="Home Assistant is not installed",
)


def _storage_key(entry_id: str) -> str:
    return f"{STORAGE_KEY}_{entry_id}"


@pytest.mark.asyncio
async def test_ha_store_migrates_v1_envelope(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
) -> None:
    """WasherCycleStorage.async_load migrates a v1 HA Store envelope without error."""
    entry_id = "migration-entry"
    storage_key = _storage_key(entry_id)
    v1_payload = sample_v1_storage_payload(entry_id)

    hass_storage[storage_key] = {
        "version": 1,
        "minor_version": 1,
        "key": storage_key,
        "data": copy.deepcopy(v1_payload),
    }

    storage = WasherCycleStorage(hass, entry_id)
    loaded = await storage.async_load()

    assert loaded["version"] == STORAGE_VERSION
    assert "announcement_state" not in loaded
    assert loaded["pending_program"] == "quick_wash"
    assert loaded["current_cycle"]["cycle_id"] == "cycle-live"
    assert loaded["training_runs"][0]["run_id"] == "run-calibration-1"
    assert loaded["profiles"]["daily_wash"]["recognition_ready"] is False
    assert loaded["profiles"]["daily_wash"]["profile_schema_version"] == 2
    assert loaded["training_runs"][0]["schema_version"] == 2
    assert "manual_timing" in loaded["training_runs"][0]["anomaly_flags"]

    assert hass_storage[storage_key]["version"] == STORAGE_VERSION
    assert "announcement_state" not in hass_storage[storage_key]["data"]

    await storage.async_save_now()
    reloaded = await storage.async_load()
    assert reloaded == loaded
    assert "announcement_state" not in reloaded
    assert reloaded["training_runs"][0]["anomaly_flags"].count("manual_timing") == 1


@pytest.mark.asyncio
async def test_ha_store_v1_envelope_uses_same_key(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
) -> None:
    """Migration keeps the historical washercycle.storage_{entry_id} key."""
    entry_id = "legacy-install"
    storage_key = _storage_key(entry_id)
    hass_storage[storage_key] = {
        "version": 1,
        "minor_version": 1,
        "key": storage_key,
        "data": sample_v1_storage_payload(entry_id),
    }

    store = Store(hass, STORAGE_VERSION, storage_key)
    migrated = await store.async_load()

    assert migrated is not None
    assert store.key == storage_key
    assert hass_storage[storage_key]["key"] == storage_key
