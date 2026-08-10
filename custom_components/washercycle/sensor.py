"""Sensor platform for WasherCycle."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_WASHERCYCLE, DOMAIN, PROGRAM_CATALOGUE
from .coordinator import WasherCycleCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WasherCycle sensors."""
    coordinator: WasherCycleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WasherCycleStateSensor(coordinator, entry),
            WasherCycleProgramSensor(coordinator, entry),
            WasherCycleProgressSensor(coordinator, entry),
            WasherCycleTimeRemainingSensor(coordinator, entry),
            WasherCycleExpectedCompletionSensor(coordinator, entry),
            WasherCycleLastCycleDurationSensor(coordinator, entry),
            WasherCycleLastCycleEnergySensor(coordinator, entry),
            WasherCycleProgramConfidenceSensor(coordinator, entry),
            WasherCycleEtaConfidenceSensor(coordinator, entry),
        ]
    )


class WasherCycleSensorBase(CoordinatorEntity, SensorEntity):
    """Base WasherCycle sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return self.coordinator.detector is not None


class WasherCycleStateSensor(WasherCycleSensorBase):
    """Primary cycle state sensor."""

    _attr_translation_key = "state"
    _attr_icon = "mdi:washing-machine"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_state"

    @property
    def native_value(self) -> str:
        if self.coordinator.detector:
            return self.coordinator.detector.cycle.public_state
        return "unavailable"

    @property
    def extra_state_attributes(self) -> dict:
        cycle = self.coordinator.detector.cycle if self.coordinator.detector else None
        if not cycle:
            return {ATTR_WASHERCYCLE: True}
        return {
            ATTR_WASHERCYCLE: True,
            "cycle_id": cycle.cycle_id,
            "detected_program": cycle.detected_program,
            "completion_reason": cycle.completion_reason,
            "match_rejection_reason": cycle.match_rejection_reason,
        }


class WasherCycleProgramSensor(WasherCycleSensorBase):
    """Detected program sensor."""

    _attr_translation_key = "program"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_program"

    @property
    def native_value(self) -> str:
        if self.coordinator.detector and self.coordinator.detector.cycle.detected_program:
            pid = self.coordinator.detector.cycle.detected_program
            return PROGRAM_CATALOGUE.get(pid, pid)
        return "Unknown"


class WasherCycleProgressSensor(WasherCycleSensorBase):
    """Cycle progress sensor."""

    _attr_translation_key = "progress"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_progress"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.detector:
            return round(self.coordinator.detector.cycle.progress, 1)
        return None


class WasherCycleTimeRemainingSensor(WasherCycleSensorBase):
    """Time remaining sensor."""

    _attr_translation_key = "time_remaining"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_time_remaining"

    @property
    def native_value(self) -> int | None:
        if self.coordinator.detector:
            return self.coordinator.detector.cycle.time_remaining_seconds
        return None


class WasherCycleExpectedCompletionSensor(WasherCycleSensorBase):
    """Expected completion timestamp sensor."""

    _attr_translation_key = "expected_completion"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_expected_completion"

    @property
    def native_value(self) -> datetime | None:
        if not self.coordinator.detector:
            return None
        raw = self.coordinator.detector.cycle.expected_completion_at
        if not raw:
            return None
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))


class WasherCycleLastCycleDurationSensor(WasherCycleSensorBase):
    """Last completed cycle duration."""

    _attr_translation_key = "last_cycle_duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_cycle_duration"

    @property
    def native_value(self) -> int | None:
        summary = (
            self.coordinator.data.get("last_cycle_summary", {}) if self.coordinator.data else {}
        )
        return summary.get("duration_seconds")


class WasherCycleLastCycleEnergySensor(WasherCycleSensorBase):
    """Last completed cycle energy."""

    _attr_translation_key = "last_cycle_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_cycle_energy"

    @property
    def native_value(self) -> float | None:
        summary = (
            self.coordinator.data.get("last_cycle_summary", {}) if self.coordinator.data else {}
        )
        return summary.get("energy_wh")


class WasherCycleProgramConfidenceSensor(WasherCycleSensorBase):
    """Program confidence sensor."""

    _attr_translation_key = "program_confidence"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_program_confidence"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.detector:
            return round(self.coordinator.detector.cycle.program_confidence * 100, 1)
        return None


class WasherCycleEtaConfidenceSensor(WasherCycleSensorBase):
    """ETA confidence sensor."""

    _attr_translation_key = "eta_confidence"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_eta_confidence"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.detector:
            return self.coordinator.detector.cycle.eta_confidence
        return None
