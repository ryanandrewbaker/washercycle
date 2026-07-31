"""Button platform for WasherCycle."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WasherCycleCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WasherCycle buttons."""
    coordinator: WasherCycleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WasherCycleStartRecordingButton(coordinator, entry),
            WasherCycleMarkCompleteButton(coordinator, entry),
            WasherCycleCancelRecordingButton(coordinator, entry),
            WasherCycleConfirmProgramButton(coordinator, entry),
            WasherCycleRebuildProfilesButton(coordinator, entry),
            WasherCycleExportDiagnosticsButton(coordinator, entry),
        ]
    )


class WasherCycleButtonBase(CoordinatorEntity, ButtonEntity):
    """Base button entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info


class WasherCycleStartRecordingButton(WasherCycleButtonBase):
    """Start training recording button."""

    _attr_translation_key = "start_recording"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_start_recording"

    async def async_press(self) -> None:
        program = self.coordinator.storage.get_pending_program()
        if program == "auto":
            program = "daily_wash"
        await self.coordinator.async_start_recording(program)


class WasherCycleMarkCompleteButton(WasherCycleButtonBase):
    """Mark complete and save button."""

    _attr_translation_key = "mark_complete"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_mark_complete"

    async def async_press(self) -> None:
        await self.coordinator.async_mark_complete()


class WasherCycleCancelRecordingButton(WasherCycleButtonBase):
    """Cancel recording button."""

    _attr_translation_key = "cancel_recording"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_cancel_recording"

    async def async_press(self) -> None:
        await self.coordinator.async_cancel_recording()


class WasherCycleConfirmProgramButton(WasherCycleButtonBase):
    """Confirm detected program button."""

    _attr_translation_key = "confirm_program"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_confirm_program"

    async def async_press(self) -> None:
        if self.coordinator.detector and self.coordinator.detector.cycle.detected_program:
            from .models import ProgramMatchState

            self.coordinator.detector.cycle.program_source = "manual"
            self.coordinator.detector.cycle.program_match_state = ProgramMatchState.MANUAL
            self.coordinator.storage.set_cycle(self.coordinator.detector.cycle)
            await self.coordinator.storage.async_save(immediate=True)
            self.coordinator.async_set_updated_data(self.coordinator.data)


class WasherCycleRebuildProfilesButton(WasherCycleButtonBase):
    """Rebuild profiles button."""

    _attr_translation_key = "rebuild_profiles"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_rebuild_profiles"

    async def async_press(self) -> None:
        await self.coordinator._rebuild_profiles()
        await self.coordinator.storage.async_save(immediate=True)
        self.coordinator.async_set_updated_data(self.coordinator.data)


class WasherCycleExportDiagnosticsButton(WasherCycleButtonBase):
    """Export diagnostics button."""

    _attr_translation_key = "export_diagnostics"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_export_diagnostics"

    async def async_press(self) -> None:
        from .diagnostics import async_get_diagnostics

        await async_get_diagnostics(self.hass, self.coordinator.entry)
