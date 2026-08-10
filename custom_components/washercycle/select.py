"""Select platform for WasherCycle."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROGRAM_CATALOGUE, PROGRAM_SELECT_OPTIONS
from .coordinator import WasherCycleCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WasherCycle selects."""
    coordinator: WasherCycleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WasherCycleNextProgramSelect(coordinator, entry)])


class WasherCycleSelectBase(CoordinatorEntity, SelectEntity):
    """Base select entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info


class WasherCycleNextProgramSelect(WasherCycleSelectBase):
    """Calibration programme selector for the next detected cycle."""

    _attr_translation_key = "next_program"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_program_select"
        self._attr_options = ["Auto"] + [
            PROGRAM_CATALOGUE[p] for p in PROGRAM_SELECT_OPTIONS if p != "auto"
        ]

    @property
    def current_option(self) -> str | None:
        pending = self.coordinator.storage.get_pending_program()
        if pending == "auto":
            return "Auto"
        return PROGRAM_CATALOGUE.get(pending, pending)

    async def async_select_option(self, option: str) -> None:
        """Select programme label for next cycle."""
        if option == "Auto":
            pid = "auto"
        else:
            pid = next(
                (k for k, v in PROGRAM_CATALOGUE.items() if v == option),
                option,
            )
        await self.coordinator.async_set_pending_program(pid)
