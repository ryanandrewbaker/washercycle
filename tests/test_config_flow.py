"""Config and options flow tests."""

from __future__ import annotations

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.washercycle.config_flow import _default_options
from custom_components.washercycle.const import (
    CONF_DOOR_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_MOVEMENT_SENSOR,
    CONF_PLUG_SWITCH,
    CONF_POWER_SENSOR,
    DEFAULT_LEGACY_STATUS_MIRROR,
    DEFAULT_REWASH_DELAY_MINUTES,
    DEFAULT_SHADOW_MODE,
    DOMAIN,
    OPT_ADVANCED_DIAGNOSTICS,
    OPT_LEGACY_STATUS_MIRROR,
    OPT_REWASH_DELAY_MINUTES,
    OPT_SHADOW_MODE,
)
from tests.helpers.ha_installed import home_assistant_installed

pytestmark = [
    pytest.mark.usefixtures("enable_custom_integrations"),
    pytest.mark.skipif(
        not home_assistant_installed(),
        reason="Home Assistant is not installed",
    ),
]


def _entry_data() -> dict[str, str]:
    return {
        CONF_POWER_SENSOR: "sensor.washer_power",
        CONF_ENERGY_SENSOR: "sensor.washer_energy",
        CONF_DOOR_SENSOR: "binary_sensor.washer_door",
        CONF_MOVEMENT_SENSOR: "binary_sensor.washer_moving",
        CONF_PLUG_SWITCH: "switch.washer_plug",
    }


@pytest.mark.asyncio
async def test_options_flow_loads_and_saves(hass: HomeAssistant) -> None:
    """Options flow opens without error and persists saved options after reload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WasherCycle",
        data=_entry_data(),
        options=_default_options(),
    )
    entry.add_to_hass(hass)

    hass.states.async_set("sensor.washer_power", "12", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.washer_energy", "1.2", {"unit_of_measurement": "kWh"})
    hass.states.async_set("binary_sensor.washer_door", "off")
    hass.states.async_set("binary_sensor.washer_moving", "off")
    hass.states.async_set("switch.washer_plug", "on")

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {}

    suggested = result["data_schema"].schema
    shadow_default = suggested[OPT_SHADOW_MODE].default()
    assert shadow_default is DEFAULT_SHADOW_MODE

    saved_options = {
        OPT_SHADOW_MODE: False,
        OPT_LEGACY_STATUS_MIRROR: True,
        OPT_REWASH_DELAY_MINUTES: 90,
        OPT_ADVANCED_DIAGNOSTICS: True,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=saved_options,
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == saved_options

    await hass.async_block_till_done()

    updated = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated is not None
    assert updated.options == saved_options
    assert updated.options[OPT_SHADOW_MODE] is False
    assert updated.options[OPT_LEGACY_STATUS_MIRROR] is True
    assert updated.options[OPT_REWASH_DELAY_MINUTES] == 90
    assert updated.options[OPT_ADVANCED_DIAGNOSTICS] is True


@pytest.mark.asyncio
async def test_new_installation_defaults_shadow_mode_true(hass: HomeAssistant) -> None:
    """New config entries keep shadow mode enabled by default."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WasherCycle",
        data=_entry_data(),
        options=_default_options(),
    )
    entry.add_to_hass(hass)

    assert entry.options[OPT_SHADOW_MODE] is True
    assert entry.options[OPT_LEGACY_STATUS_MIRROR] is DEFAULT_LEGACY_STATUS_MIRROR
    assert entry.options[OPT_REWASH_DELAY_MINUTES] == DEFAULT_REWASH_DELAY_MINUTES
    assert entry.options[OPT_ADVANCED_DIAGNOSTICS] is False


@pytest.mark.asyncio
async def test_reconfigure_flow_updates_entry_data(hass: HomeAssistant) -> None:
    """Reconfigure remains separate from Options and updates integration data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WasherCycle",
        data=_entry_data(),
        options=_default_options(),
    )
    entry.add_to_hass(hass)

    hass.states.async_set("sensor.washer_power", "12", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.washer_energy", "1.2", {"unit_of_measurement": "kWh"})
    hass.states.async_set("binary_sensor.washer_door", "off")

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    updated_data = {
        **entry.data,
        CONF_POWER_SENSOR: "sensor.new_washer_power",
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=updated_data,
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    await hass.async_block_till_done()

    reloaded = hass.config_entries.async_get_entry(entry.entry_id)
    assert reloaded is not None
    assert reloaded.data[CONF_POWER_SENSOR] == "sensor.new_washer_power"
    assert reloaded.options[OPT_SHADOW_MODE] is True


@pytest.fixture(autouse=True)
async def _unload_washercycle_entries(hass: HomeAssistant):
    yield
    for entry in list(hass.config_entries.async_entries("washercycle")):
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
