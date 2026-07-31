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
    async_add_entities(
        [
            WasherCycleProgramSelect(coordinator, entry),
            WasherCycleTrainingProgramSelect(coordinator, entry),
        ]
    )


class WasherCycleSelectBase(CoordinatorEntity, SelectEntity):
    """Base select entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info


class WasherCycleProgramSelect(WasherCycleSelectBase):
    """Manual program selection for next cycle."""

    _attr_translation_key = "program_select"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_program_select"
        self._attr_options = [PROGRAM_CATALOGUE.get(p, p) for p in PROGRAM_SELECT_OPTIONS]

    @property
    def current_option(self) -> str | None:
        pending = self.coordinator.storage.get_pending_program()
        if pending == "auto":
            return "auto"
        return PROGRAM_CATALOGUE.get(pending, pending)

    async def async_select_option(self, option: str) -> None:
        """Select program for next cycle."""
        if option == "auto":
            pid = "auto"
        else:
            pid = next(
                (k for k, v in PROGRAM_CATALOGUE.items() if v == option),
                option,
            )
        await self.coordinator.async_set_pending_program(pid)


class WasherCycleTrainingProgramSelect(WasherCycleSelectBase):
    """Training program selection."""

    _attr_translation_key = "training_program_select"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_training_program_select"
        self._attr_options = list(PROGRAM_CATALOGUE.values())
        self._training_program = "daily_wash"

    @property
    def current_option(self) -> str | None:
        rec = self.coordinator.recorder.recording
        if rec.active and rec.program_id:
            return PROGRAM_CATALOGUE.get(rec.program_id, rec.program_id)
        return PROGRAM_CATALOGUE.get(self._training_program, self._training_program)

    async def async_select_option(self, option: str) -> None:
        """Select training program."""
        pid = next((k for k, v in PROGRAM_CATALOGUE.items() if v == option), option)
        self._training_program = pid
        await self.coordinator.async_set_pending_program(pid)
