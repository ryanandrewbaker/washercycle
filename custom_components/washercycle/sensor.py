"""Sensor platform for WasherCycle."""

from __future__ import annotations

from datetime import timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
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
            WasherCycleCycleDurationSensor(coordinator, entry),
            WasherCycleCycleEnergySensor(coordinator, entry),
            WasherCycleLastCycleDurationSensor(coordinator, entry),
            WasherCycleLastCycleEnergySensor(coordinator, entry),
            WasherCycleProgramConfidenceSensor(coordinator, entry),
            WasherCycleEtaConfidenceSensor(coordinator, entry),
            WasherCycleCompletionLatencySensor(coordinator, entry),
            WasherCycleTrainingRunsSensor(coordinator, entry),
            WasherCycleRecordingDurationSensor(coordinator, entry),
            WasherCycleRecordingEnergySensor(coordinator, entry),
        ]
    )


class WasherCycleSensorBase(CoordinatorEntity, SensorEntity):
    """Base WasherCycle sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
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
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict:
        cycle = self.coordinator.detector.cycle if self.coordinator.detector else None
        if not cycle:
            return {ATTR_WASHERCYCLE: True}
        return {
            ATTR_WASHERCYCLE: True,
            "cycle_id": cycle.cycle_id,
            "detected_program": cycle.detected_program,
            "selected_program": cycle.selected_program,
            "state_reason": cycle.state_reason,
            "program_confidence": cycle.program_confidence,
            "eta_confidence": cycle.eta_confidence,
            "expected_completion": cycle.expected_completion_at,
            "completion_evidence": cycle.pending_end_evidence,
            "source_availability": cycle.source_availability,
            "last_transition": cycle.last_transition_at,
            "door_correlation_pending": cycle.door_open_pending_at is not None,
        }


class WasherCycleProgramSensor(WasherCycleSensorBase):
    """Detected program sensor."""

    _attr_translation_key = "program"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_program"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.detector and self.coordinator.detector.cycle.detected_program:
            pid = self.coordinator.detector.cycle.detected_program
            return PROGRAM_CATALOGUE.get(pid, pid)
        return None


class WasherCycleProgressSensor(WasherCycleSensorBase):
    """Cycle progress sensor."""

    _attr_translation_key = "progress"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

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
    def native_value(self) -> str | None:
        if self.coordinator.detector:
            return self.coordinator.detector.cycle.expected_completion_at
        return None


class WasherCycleCycleDurationSensor(WasherCycleSensorBase):
    """Current cycle duration."""

    _attr_translation_key = "cycle_duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_cycle_duration"

    @property
    def native_value(self) -> int | None:
        cycle = self.coordinator.detector.cycle if self.coordinator.detector else None
        if cycle and cycle.started_at:
            from datetime import datetime

            start = datetime.fromisoformat(cycle.started_at.replace("Z", "+00:00"))
            return int((datetime.now(timezone.utc) - start).total_seconds())
        return None


class WasherCycleCycleEnergySensor(WasherCycleSensorBase):
    """Current cycle energy."""

    _attr_translation_key = "cycle_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_cycle_energy"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.detector:
            return round(self.coordinator.detector.cycle.accumulated_energy_wh, 2)
        return None


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
        summary = self.coordinator.data.get("last_cycle_summary", {}) if self.coordinator.data else {}
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
        summary = self.coordinator.data.get("last_cycle_summary", {}) if self.coordinator.data else {}
        return summary.get("energy_wh")


class WasherCycleProgramConfidenceSensor(WasherCycleSensorBase):
    """Program confidence sensor."""

    _attr_translation_key = "program_confidence"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_program_confidence"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.detector:
            return round(self.coordinator.detector.cycle.program_confidence, 2)
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


class WasherCycleCompletionLatencySensor(WasherCycleSensorBase):
    """Completion detection latency sensor."""

    _attr_translation_key = "completion_latency"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_completion_latency"

    @property
    def native_value(self) -> float | None:
        stats = self.coordinator.storage.get_latency_stats()
        return round(stats.median_seconds, 1) if stats.median_seconds else None


class WasherCycleTrainingRunsSensor(WasherCycleSensorBase):
    """Training run count sensor."""

    _attr_translation_key = "training_runs"

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_training_runs"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.storage.get_training_runs())


class WasherCycleRecordingDurationSensor(WasherCycleSensorBase):
    """Active recording duration."""

    _attr_translation_key = "recording_duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_recording_duration"

    @property
    def native_value(self) -> int | None:
        rec = self.coordinator.recorder.recording
        if rec.active and rec.started_at:
            from datetime import datetime

            start = datetime.fromisoformat(rec.started_at.replace("Z", "+00:00"))
            return int((datetime.now(timezone.utc) - start).total_seconds())
        return None


class WasherCycleRecordingEnergySensor(WasherCycleSensorBase):
    """Active recording energy."""

    _attr_translation_key = "recording_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

    def __init__(self, coordinator: WasherCycleCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_recording_energy"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.recorder.is_active and self.coordinator.detector:
            return round(self.coordinator.detector.cycle.accumulated_energy_wh, 2)
        return None
