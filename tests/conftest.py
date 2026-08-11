"""Pytest configuration for WasherCycle."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

try:
    import homeassistant  # noqa: F401

    HA_INSTALLED = True
except ImportError:
    HA_INSTALLED = False

if HA_INSTALLED:
    pytest_plugins = ("pytest_homeassistant_custom_component.common",)

    @pytest.fixture(autouse=True)
    def auto_enable_custom_integrations(enable_custom_integrations):
        """Load custom_components/washercycle for integration tests."""
        return enable_custom_integrations

    @pytest.fixture(autouse=True)
    async def unload_config_entries(hass):
        """Unload WasherCycle entries so coordinator timers do not linger."""
        yield
        for entry in list(hass.config_entries.async_entries()):
            if entry.domain == "washercycle":
                await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

# Mock homeassistant for pure domain tests when HA is not installed
if not HA_INSTALLED and "homeassistant" not in sys.modules:
    ha = ModuleType("homeassistant")
    ha_core = ModuleType("homeassistant.core")
    ha_config_entries = ModuleType("homeassistant.config_entries")
    ha_const = ModuleType("homeassistant.const")
    ha_helpers_storage = ModuleType("homeassistant.helpers.storage")
    ha_helpers_event = ModuleType("homeassistant.helpers.event")
    ha_helpers_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
    ha_helpers_device_registry = ModuleType("homeassistant.helpers.device_registry")
    ha_helpers_entity_platform = ModuleType("homeassistant.helpers.entity_platform")
    ha_components_sensor = ModuleType("homeassistant.components.sensor")
    ha_components_binary_sensor = ModuleType("homeassistant.components.binary_sensor")
    ha_components_select = ModuleType("homeassistant.components.select")
    ha_components_button = ModuleType("homeassistant.components.button")

    class _HomeAssistant:
        pass

    class _ConfigEntry:
        pass

    class _DataUpdateCoordinator:
        def __init__(self, *args, **kwargs):
            self.data = {}

    class _Store:
        def __init__(self, *args, **kwargs):
            self._data = None

        async def async_load(self):
            return self._data

        async def async_save(self, data):
            self._data = data

    ha_core.HomeAssistant = _HomeAssistant
    ha_core.ServiceCall = MagicMock
    ha_core.callback = lambda f: f
    ha_config_entries.ConfigEntry = _ConfigEntry
    ha_config_entries.ConfigFlow = type("ConfigFlow", (), {})
    ha_config_entries.OptionsFlow = type("OptionsFlow", (), {})
    ha_const.Platform = MagicMock()
    ha_const.PERCENTAGE = "%"
    ha_const.UnitOfEnergy = MagicMock(WATT_HOUR="Wh")
    ha_const.UnitOfTime = MagicMock(SECONDS="s")
    ha_const.STATE_ON = "on"
    ha_const.STATE_UNAVAILABLE = "unavailable"
    ha_const.STATE_UNKNOWN = "unknown"
    ha_const.CONF_NAME = "name"
    ha_helpers_storage.Store = _Store
    ha_helpers_event.async_track_state_change_event = MagicMock(return_value=lambda: None)
    ha_helpers_update_coordinator.DataUpdateCoordinator = _DataUpdateCoordinator
    ha_helpers_device_registry.async_get = MagicMock()
    ha_helpers_entity_platform.AddEntitiesCallback = MagicMock
    ha_components_sensor.SensorEntity = type("SensorEntity", (), {})
    ha_components_sensor.SensorDeviceClass = MagicMock(
        DURATION="duration", ENERGY="energy", TIMESTAMP="timestamp"
    )
    ha_components_sensor.SensorStateClass = MagicMock(
        MEASUREMENT="measurement", TOTAL_INCREASING="total_increasing"
    )
    ha_components_binary_sensor.BinarySensorEntity = type("BinarySensorEntity", (), {})
    ha_components_select.SelectEntity = type("SelectEntity", (), {})
    ha_components_button.ButtonEntity = type("ButtonEntity", (), {})

    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.config_entries"] = ha_config_entries
    sys.modules["homeassistant.const"] = ha_const
    sys.modules["homeassistant.helpers"] = ModuleType("homeassistant.helpers")
    sys.modules["homeassistant.helpers.storage"] = ha_helpers_storage
    sys.modules["homeassistant.helpers.event"] = ha_helpers_event
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_helpers_update_coordinator
    sys.modules["homeassistant.helpers.device_registry"] = ha_helpers_device_registry
    sys.modules["homeassistant.helpers.entity_platform"] = ha_helpers_entity_platform
    sys.modules["homeassistant.helpers.selector"] = ModuleType("homeassistant.helpers.selector")
    sys.modules["homeassistant.data_entry_flow"] = ModuleType("homeassistant.data_entry_flow")
    sys.modules["homeassistant.components.sensor"] = ha_components_sensor
    sys.modules["homeassistant.components.binary_sensor"] = ha_components_binary_sensor
    sys.modules["homeassistant.components.select"] = ha_components_select
    sys.modules["homeassistant.components.button"] = ha_components_button

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from custom_components.washercycle.models import DetectorConfig  # noqa: E402


@pytest.fixture
def detector_config() -> DetectorConfig:
    """Default detector config for tests."""
    return DetectorConfig(
        start_power_w=19.0,
        standby_power_w=5.0,
        start_sustain_seconds=5,
        start_min_energy_wh=0.1,
        fallback_completion_seconds=60,
        early_completion_enabled=False,
        early_completion_min_score=0.75,
        door_correlation_seconds=30,
        shadow_mode=True,
        rewash_delay_minutes=120,
        standby_confirm_seconds=60.0,
        post_completion_seconds=30,
    )


@pytest.fixture
def base_time() -> datetime:
    """Base timestamp for replay tests."""
    return datetime(2026, 7, 31, 10, 0, 0, tzinfo=UTC)


def make_power_events(
    base: datetime,
    values: list[tuple[int, float]],
) -> list[dict]:
    """Create power events at offsets."""
    return [
        {"timestamp": base + timedelta(seconds=offset), "kind": "power", "value": w}
        for offset, w in values
    ]
