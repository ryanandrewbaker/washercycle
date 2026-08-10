"""Setup entry regression tests for v1 storage migration."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.washercycle.const import (
    CONF_DOOR_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_POWER_SENSOR,
    DOMAIN,
    STORAGE_KEY,
)
from custom_components.washercycle.setup_entry import async_setup_entry, async_unload_entry
from tests.helpers.v1_storage import sample_v1_storage_payload


def _home_assistant_installed() -> bool:
    try:
        from homeassistant import __version__ as _ha_version  # noqa: F401

        return bool(_ha_version)
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _home_assistant_installed(),
    reason="Home Assistant is not installed",
)


@pytest.mark.asyncio
async def test_setup_entry_loads_existing_v1_storage(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
) -> None:
    """An existing v1 installation can run async_setup_entry without migration errors."""
    entry_id = "setup-v1-entry"
    storage_key = f"{STORAGE_KEY}_{entry_id}"
    hass_storage[storage_key] = {
        "version": 1,
        "minor_version": 1,
        "key": storage_key,
        "data": copy.deepcopy(sample_v1_storage_payload(entry_id)),
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        title="WasherCycle",
        data={
            CONF_POWER_SENSOR: "sensor.washer_power",
            CONF_ENERGY_SENSOR: "sensor.washer_energy",
            CONF_DOOR_SENSOR: "binary_sensor.washer_door",
        },
        options={"shadow_mode": True},
    )
    entry.add_to_hass(hass)

    hass.states.async_set("sensor.washer_power", "12", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.washer_energy", "1.2", {"unit_of_measurement": "kWh"})
    hass.states.async_set("binary_sensor.washer_door", "off")

    assert await async_setup_entry(hass, entry)

    coordinator = hass.data[DOMAIN][entry_id]
    assert coordinator.storage.get_pending_program() == "quick_wash"
    assert coordinator.storage.get_cycle().cycle_id == "cycle-live"
    assert coordinator.storage.get_training_runs()[0].run_id == "run-calibration-1"
    assert "announcement_state" not in coordinator.storage.data
    assert coordinator.storage.data["profiles"]["daily_wash"]["profile_schema_version"] == 2

    assert await async_unload_entry(hass, entry)
