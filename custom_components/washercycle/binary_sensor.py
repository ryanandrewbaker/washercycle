"""Binary sensor platform for WasherCycle."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WasherCycleCoordinator
from .models import InternalState

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WasherCycle binary sensors."""
    coordinator: WasherCycleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WasherCycleRunningBinarySensor(coordinator, entry),
            WasherCycleNeedsEmptyingBinarySensor(coordinator, entry),
        ]
    )


class WasherCycleBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base binary sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info


class WasherCycleRunningBinarySensor(WasherCycleBinarySensorBase):
    """Running binary sensor."""

    _attr_translation_key = "running"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_running"

    @property
    def is_on(self) -> bool:
        if not self.coordinator.detector:
            return False
        return self.coordinator.detector.cycle.internal_state in (
            InternalState.RUNNING,
            InternalState.PAUSED,
            InternalState.START_CANDIDATE,
        )


class WasherCycleNeedsEmptyingBinarySensor(WasherCycleBinarySensorBase):
    """Needs emptying binary sensor."""

    _attr_translation_key = "needs_emptying"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_needs_emptying"

    @property
    def is_on(self) -> bool:
        if not self.coordinator.detector:
            return False
        return self.coordinator.detector.cycle.internal_state == InternalState.NEEDS_EMPTYING
