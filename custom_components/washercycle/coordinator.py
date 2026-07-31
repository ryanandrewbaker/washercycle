"""Data update coordinator for WasherCycle."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .announcements import AnnouncementManager
from .const import (
    CONF_DOOR_BATTERY_LOW_SENSOR,
    CONF_DOOR_BATTERY_SENSOR,
    CONF_DOOR_LQI_SENSOR,
    CONF_DOOR_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_MOVEMENT_SENSOR,
    CONF_PLUG_LQI_SENSOR,
    CONF_PLUG_SWITCH,
    CONF_POWER_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    DOMAIN,
    EVENT_TRAINING_CANCELLED,
    EVENT_TRAINING_SAVED,
    EVENT_TRAINING_STARTED,
    OPT_LEGACY_STATUS_MIRROR,
    OPT_RESAMPLE_INTERVAL_SECONDS,
    OPT_REWASH_DELAY_MINUTES,
    OPT_SHADOW_MODE,
    PROGRAM_CATALOGUE,
)
from .detector import CycleDetector, DetectorInput
from .models import DetectorConfig, InternalState
from .normalizer import InputNormalizer, NormalizerState
from .profiles import build_profile_from_runs
from .storage import WasherCycleStorage
from .training import TrainingRecorder

_LOGGER = logging.getLogger(__name__)


class WasherCycleCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for WasherCycle integration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self.entry = entry
        self.storage = WasherCycleStorage(hass, entry.entry_id)
        self.normalizer = InputNormalizer()
        self.detector: CycleDetector | None = None
        self.recorder = TrainingRecorder()
        self.announcements: AnnouncementManager | None = None
        self._unsubscribers: list[CALLBACK_TYPE] = []
        self._entity_ids: list[str] = []
        self._last_cycle_summary: dict[str, Any] = {}
        self.device_info: dict[str, Any] = {}

    @property
    def options(self) -> dict[str, Any]:
        return {**self.entry.options}

    @property
    def config(self) -> dict[str, Any]:
        return self.entry.data

    def detector_config(self) -> DetectorConfig:
        """Build detector config from options."""
        opts = self.options
        return DetectorConfig(
            start_power_w=float(opts.get("start_power_w", 19.0)),
            standby_power_w=float(opts.get("standby_power_w", 5.0)),
            start_sustain_seconds=float(opts.get("start_sustain_seconds", 30)),
            start_min_energy_wh=float(opts.get("start_min_energy_wh", 1.0)),
            fallback_completion_seconds=float(opts.get("fallback_completion_seconds", 300)),
            early_completion_enabled=bool(opts.get("early_completion_enabled", True)),
            early_completion_min_score=float(opts.get("early_completion_min_score", 0.75)),
            door_correlation_seconds=float(opts.get("door_correlation_seconds", 30)),
            movement_enabled=bool(opts.get("movement_enabled", True)),
            max_stale_seconds=float(opts.get("max_stale_seconds", 120)),
            shadow_mode=bool(opts.get(OPT_SHADOW_MODE, True)),
            rewash_delay_minutes=int(opts.get(OPT_REWASH_DELAY_MINUTES, 120)),
            min_runs_recognition=int(opts.get("min_runs_recognition", 3)),
            min_runs_robust=int(opts.get("min_runs_robust", 5)),
            resample_interval_seconds=int(opts.get("resample_interval_seconds", 15)),
            matcher_margin=float(opts.get("matcher_margin", 0.12)),
        )

    async def async_setup(self) -> None:
        """Set up coordinator."""
        await self.storage.async_load()

        norm_state = self.storage.get_normalizer_state()
        if norm_state:
            self.normalizer = InputNormalizer(NormalizerState.from_dict(norm_state))

        cycle = self.storage.get_cycle()
        profiles = self.storage.get_profiles()
        pending = self.storage.get_pending_program()

        self.detector = CycleDetector(
            config=self.detector_config(),
            cycle=cycle,
            profiles={pid: p for pid, p in profiles.items()},
            pending_program=pending,
        )

        if cycle.restart_recovered or cycle.internal_state != InternalState.IDLE:
            self.detector.restore(cycle, pending)

        self.recorder.restore(self.storage.get_recording())
        self.announcements = AnnouncementManager(
            hass=self.hass,
            options=self.options,
            announcement_state=self.storage.get_announcement_state(),
        )

        self._entity_ids = self._source_entities()
        self._subscribe_sources()
        await self._async_update_data()

    async def async_shutdown(self) -> None:
        """Shut down coordinator."""
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        if self.detector:
            self.storage.set_cycle(self.detector.cycle)
        self.storage.set_recording(self.recorder.recording)
        self.storage.set_normalizer_state(self.normalizer.state.to_dict())
        if self.announcements:
            self.storage.set_announcement_state(self.announcements.state)
        await self.storage.async_save_now()

    def _source_entities(self) -> list[str]:
        data = self.config
        entities = [
            data[CONF_POWER_SENSOR],
            data[CONF_ENERGY_SENSOR],
            data[CONF_PLUG_SWITCH],
            data[CONF_DOOR_SENSOR],
            data[CONF_MOVEMENT_SENSOR],
        ]
        for key in (
            CONF_TEMPERATURE_SENSOR,
            CONF_PLUG_LQI_SENSOR,
            CONF_DOOR_LQI_SENSOR,
            CONF_DOOR_BATTERY_SENSOR,
            CONF_DOOR_BATTERY_LOW_SENSOR,
        ):
            if data.get(key):
                entities.append(data[key])
        return entities

    def _subscribe_sources(self) -> None:
        @callback
        def _state_changed(event: Any) -> None:
            self.hass.async_create_task(self._handle_state_change(event))

        self._unsubscribers.append(
            async_track_state_change_event(self.hass, self._entity_ids, _state_changed)
        )

    async def _handle_state_change(self, event: Any) -> None:
        await self._process_current_states(event.data.get("time_fired"))
        self.async_set_updated_data(self.data)

    async def _async_update_data(self) -> dict[str, Any]:
        await self._process_current_states()
        return self.data

    async def _process_current_states(self, timestamp: datetime | None = None) -> None:
        if not self.detector:
            return

        now = timestamp or datetime.now(timezone.utc)
        data = self.config

        power_state = self.hass.states.get(data[CONF_POWER_SENSOR])
        energy_state = self.hass.states.get(data[CONF_ENERGY_SENSOR])
        door_state = self.hass.states.get(data[CONF_DOOR_SENSOR])
        movement_state = self.hass.states.get(data[CONF_MOVEMENT_SENSOR])
        plug_state = self.hass.states.get(data[CONF_PLUG_SWITCH])

        power_available = power_state is not None and power_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )
        energy_available = energy_state is not None and energy_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )
        door_available = door_state is not None and door_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )
        movement_available = movement_state is not None and movement_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

        power = None
        if power_available and power_state:
            power = self.normalizer.normalize_power(
                data[CONF_POWER_SENSOR], power_state.state, now
            )

        energy = None
        if energy_available and energy_state:
            energy = self.normalizer.normalize_energy(
                data[CONF_ENERGY_SENSOR], energy_state.state, now, energy_in_kwh=True
            )

        door = None
        if door_available and door_state:
            door = self.normalizer.normalize_bool(
                data[CONF_DOOR_SENSOR], door_state.state, now, on_means_true=True
            )

        movement = None
        if movement_available and movement_state:
            movement = self.normalizer.normalize_bool(
                data[CONF_MOVEMENT_SENSOR], movement_state.state, now, on_means_true=True
            )

        plug_on = None
        if plug_state and plug_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            plug_on = plug_state.state == STATE_ON

        inp = DetectorInput(
            timestamp=now,
            power_w=power.watts if power else None,
            energy_wh=energy.watt_hours if energy else None,
            door_open=door.value if door else None,
            movement=movement.value if movement else None,
            plug_on=plug_on,
            power_available=power_available,
            energy_available=energy_available,
            door_available=door_available,
            movement_available=movement_available,
        )

        if self.recorder.is_active:
            self._record_sample(inp, now)

        result = self.detector.process(inp)
        self.storage.set_cycle(result.cycle)
        self.storage.add_transitions(result.transitions)

        for evt in result.events:
            self.hass.bus.async_fire(evt.name, {**evt.data, "config_entry_id": self.entry.entry_id})

        if self.announcements and not self.options.get(OPT_SHADOW_MODE, True):
            door_open = door.value if door else False
            for ann in result.announcement_requests:
                if ann == "completion":
                    await self.announcements.announce_completion(
                        result.cycle.cycle_id,
                        door_open=door_open,
                        immediately_emptied=result.cycle.immediately_emptied,
                    )
                elif ann == "rewash":
                    await self.announcements.announce_rewash(result.cycle.cycle_id)

        if self.options.get(OPT_LEGACY_STATUS_MIRROR):
            await self._mirror_legacy_status(result.cycle.public_state)

        if result.cycle.completed_at and result.cycle.internal_state in (
            InternalState.NEEDS_EMPTYING,
            InternalState.IDLE,
        ):
            self._last_cycle_summary = {
                "cycle_id": result.cycle.cycle_id,
                "duration": result.cycle.completed_at,
                "energy_wh": result.cycle.accumulated_energy_wh,
                "program": result.cycle.detected_program,
            }

        self.storage.set_normalizer_state(self.normalizer.state.to_dict())
        if self.announcements:
            self.storage.set_announcement_state(self.announcements.state)
        await self.storage.async_save()

        self.data = {
            "cycle": result.cycle,
            "recording": self.recorder.recording,
            "profiles": self.storage.get_profiles(),
            "training_runs": self.storage.get_training_runs(),
            "latency_stats": self.storage.get_latency_stats(),
            "last_cycle_summary": self._last_cycle_summary,
            "pending_program": self.storage.get_pending_program(),
        }

    def _record_sample(self, inp: DetectorInput, now: datetime) -> None:
        if inp.power_w is not None:
            self.recorder.add_sample(
                {"kind": "power", "timestamp": now.isoformat(), "value": inp.power_w}
            )
        if inp.energy_wh is not None:
            self.recorder.add_sample(
                {"kind": "energy", "timestamp": now.isoformat(), "value": inp.energy_wh}
            )
        if inp.movement is not None:
            self.recorder.add_sample(
                {"kind": "movement", "timestamp": now.isoformat(), "value": inp.movement}
            )
        if inp.door_open is not None:
            self.recorder.add_sample(
                {"kind": "door", "timestamp": now.isoformat(), "value": inp.door_open}
            )

    async def _mirror_legacy_status(self, public_state: str) -> None:
        mapping = {
            "idle": "Empty",
            "starting": "Washing",
            "running": "Washing",
            "paused": "Washing",
            "finishing": "Washing",
            "needs_emptying": "Needs Emptying",
            "needs_rewash": "Needs Rewash",
        }
        value = mapping.get(public_state)
        if value:
            await self.hass.services.async_call(
                "input_text",
                "set_value",
                {"entity_id": "input_text.washing_machine_status", "value": value},
            )

    async def async_start_recording(self, program_id: str | None = None) -> None:
        """Start training recording."""
        if self.recorder.is_active:
            raise ValueError("Recording already active")
        pid = program_id or self.storage.get_pending_program()
        if pid == "auto":
            pid = "daily_wash"
        run_id = self.recorder.start(pid)
        self.storage.set_recording(self.recorder.recording)
        await self.storage.async_save(immediate=True)
        self.hass.bus.async_fire(
            EVENT_TRAINING_STARTED,
            {
                "config_entry_id": self.entry.entry_id,
                "run_id": run_id,
                "program_id": pid,
            },
        )
        self.async_set_updated_data(self.data)

    async def async_mark_complete(self) -> None:
        """Mark training complete and save."""
        if not self.recorder.is_active:
            raise ValueError("No active recording")
        auto_complete = self.detector.cycle.completed_at if self.detector else None
        auto_start = self.detector.cycle.started_at if self.detector else None
        run = self.recorder.mark_complete_and_save(
            auto_detected_start_at=auto_start,
            auto_detected_complete_at=auto_complete,
            resample_interval=self.options.get(OPT_RESAMPLE_INTERVAL_SECONDS, 15),
        )
        self.storage.add_training_run(run)
        await self._rebuild_profiles(run.program_id)
        self.storage.set_recording(self.recorder.recording)
        await self.storage.async_save(immediate=True)
        self.hass.bus.async_fire(
            EVENT_TRAINING_SAVED,
            {
                "config_entry_id": self.entry.entry_id,
                "training_run_id": run.run_id,
                "program_id": run.program_id,
            },
        )
        self.async_set_updated_data(self.data)

    async def async_cancel_recording(self) -> None:
        """Cancel active recording."""
        if not self.recorder.is_active:
            raise ValueError("No active recording")
        self.recorder.cancel()
        self.storage.set_recording(self.recorder.recording)
        await self.storage.async_save(immediate=True)
        self.hass.bus.async_fire(
            EVENT_TRAINING_CANCELLED,
            {"config_entry_id": self.entry.entry_id},
        )
        self.async_set_updated_data(self.data)

    async def _rebuild_profiles(self, program_id: str | None = None) -> None:
        runs = self.storage.get_training_runs()
        profiles = self.storage.get_profiles()
        pids = [program_id] if program_id else list(PROGRAM_CATALOGUE.keys())
        for pid in pids:
            profiles[pid] = build_profile_from_runs(
                pid,
                runs,
                resample_interval_seconds=int(self.options.get("resample_interval_seconds", 15)),
                end_signature_pre_seconds=int(self.options.get("end_signature_pre_seconds", 300)),
                end_signature_post_seconds=int(self.options.get("end_signature_post_seconds", 30)),
            )
        self.storage.set_profiles(profiles)
        if self.detector:
            self.detector.profiles = profiles

    async def async_set_pending_program(self, program: str) -> None:
        """Set pending manual program."""
        self.storage.set_pending_program(program)
        await self.storage.async_save()
        self.async_set_updated_data(self.data)

    async def async_force_empty(self) -> None:
        """Force cycle to empty."""
        if self.detector:
            result = self.detector.force_empty()
            self.storage.set_cycle(result.cycle)
            for evt in result.events:
                self.hass.bus.async_fire(
                    evt.name, {**evt.data, "config_entry_id": self.entry.entry_id}
                )
            await self.storage.async_save(immediate=True)
            self.async_set_updated_data(self.data)
