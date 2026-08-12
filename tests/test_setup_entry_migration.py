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
from tests.helpers.ha_installed import home_assistant_installed
from tests.helpers.v1_storage import sample_v1_storage_payload

pytestmark = [
    pytest.mark.usefixtures("enable_custom_integrations"),
    pytest.mark.skipif(
        not home_assistant_installed(),
        reason="Home Assistant is not installed",
    ),
]


@pytest.fixture(autouse=True)
def disable_coordinator_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid interval timers during setup entry integration tests."""
    monkeypatch.setattr(
        "custom_components.washercycle.coordinator.WasherCycleCoordinator._subscribe_tick",
        lambda self: None,
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

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry_id]
    assert coordinator.storage.get_pending_program() == "auto"
    assert coordinator.storage.get_cycle().cycle_id == ""
    assert coordinator.storage.get_training_runs() == []
    assert "announcement_state" not in coordinator.storage.data
    assert coordinator.storage.data["profiles"]["daily_wash"]["profile_schema_version"] == 2

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture(autouse=True)
async def _unload_washercycle_entries(hass: HomeAssistant):
    yield
    for entry in list(hass.config_entries.async_entries("washercycle")):
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
