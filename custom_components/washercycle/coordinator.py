"""Data update coordinator for WasherCycle."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DOOR_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_MOVEMENT_SENSOR,
    CONF_PLUG_SWITCH,
    CONF_POWER_SENSOR,
    DOMAIN,
    EVENT_CYCLE_COMPLETED,
    EVENT_CYCLE_EMPTIED,
    EVENT_NEEDS_REWASH,
    EVENT_PROGRAM_IDENTIFIED,
    OPT_ADVANCED_DIAGNOSTICS,
    OPT_LEGACY_STATUS_MIRROR,
    OPT_RESAMPLE_INTERVAL_SECONDS,
    OPT_REWASH_DELAY_MINUTES,
    OPT_SHADOW_MODE,
    PROGRAM_CATALOGUE,
)
from .cycle_archive import CycleArchive
from .detector import CycleDetector, DetectorInput
from .models import DetectorConfig, InternalState, SampleSource
from .normalizer import InputNormalizer, NormalizerState
from .preset import APPLIANCE_PRESET
from .profiles import build_profile_from_runs
from .storage import WasherCycleStorage

_LOGGER = logging.getLogger(__name__)

OPERATIONAL_EVENTS = frozenset(
    {
        EVENT_CYCLE_COMPLETED,
        EVENT_CYCLE_EMPTIED,
        EVENT_NEEDS_REWASH,
        EVENT_PROGRAM_IDENTIFIED,
        "washercycle_cycle_started",
    }
)


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
        self.archive = CycleArchive(
            post_completion_seconds=int(APPLIANCE_PRESET["post_completion_seconds"])
        )
        self._unsubscribers: list[CALLBACK_TYPE] = []
        self._entity_ids: list[str] = []
        self._last_cycle_summary: dict[str, Any] = {}
        self._last_triggered_entity: str | None = None
        self._lock = asyncio.Lock()
        self.device_info: dict[str, Any] = {}

    @property
    def options(self) -> dict[str, Any]:
        return {**self.entry.options}

    @property
    def config(self) -> dict[str, Any]:
        return self.entry.data

    def detector_config(self) -> DetectorConfig:
        """Build detector config from options and appliance preset."""
        opts = self.options
        return DetectorConfig(
            start_power_w=float(APPLIANCE_PRESET["start_power_w"]),
            standby_power_w=float(APPLIANCE_PRESET["standby_power_w"]),
            start_sustain_seconds=float(APPLIANCE_PRESET["start_sustain_seconds"]),
            start_min_energy_wh=float(APPLIANCE_PRESET["start_min_energy_wh"]),
            fallback_completion_seconds=float(opts.get("fallback_completion_seconds", 300)),
            early_completion_enabled=False,
            early_completion_min_score=0.75,
            door_correlation_seconds=float(opts.get("door_correlation_seconds", 30)),
            movement_enabled=bool(opts.get("movement_enabled", True)),
            max_stale_seconds=float(opts.get("max_stale_seconds", 120)),
            shadow_mode=bool(opts.get(OPT_SHADOW_MODE, True)),
            rewash_delay_minutes=int(opts.get(OPT_REWASH_DELAY_MINUTES, 120)),
            min_runs_recognition=int(opts.get("min_runs_recognition", 3)),
            min_runs_robust=int(opts.get("min_runs_robust", 5)),
            resample_interval_seconds=int(APPLIANCE_PRESET["resample_interval_seconds"]),
            matcher_margin=float(APPLIANCE_PRESET["matcher_margin"]),
            standby_confirm_seconds=float(APPLIANCE_PRESET["standby_confirm_seconds"]),
            post_completion_seconds=int(APPLIANCE_PRESET["post_completion_seconds"]),
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

        self.archive.restore_pending(cycle)

        self._entity_ids = self._source_entities()
        self._subscribe_sources()
        self._subscribe_tick()
        await self._async_update_data()

    async def async_shutdown(self) -> None:
        """Shut down coordinator."""
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        if self.detector:
            self.storage.set_cycle(self.detector.cycle)
        self.storage.set_normalizer_state(self.normalizer.state.to_dict())
        await self.storage.async_save_now()

    def _source_entities(self) -> list[str]:
        data = self.config
        entities = [
            data[CONF_POWER_SENSOR],
            data[CONF_DOOR_SENSOR],
        ]
        if data.get(CONF_ENERGY_SENSOR):
            entities.append(data[CONF_ENERGY_SENSOR])
        if data.get(CONF_MOVEMENT_SENSOR):
            entities.append(data[CONF_MOVEMENT_SENSOR])
        if data.get(CONF_PLUG_SWITCH):
            entities.append(data[CONF_PLUG_SWITCH])
        return entities

    def _subscribe_sources(self) -> None:
        @callback
        def _state_changed(event: Any) -> None:
            entity_id = event.data.get("entity_id")
            self._last_triggered_entity = entity_id
            self.hass.async_create_task(self._handle_state_change(event))

        self._unsubscribers.append(
            async_track_state_change_event(self.hass, self._entity_ids, _state_changed)
        )

    def _tick_interval(self) -> timedelta:
        if not self.detector:
            return timedelta(seconds=int(APPLIANCE_PRESET["tick_interval_slow_seconds"]))
        state = InternalState(self.detector.cycle.internal_state)
        fast_states = {
            InternalState.START_CANDIDATE,
            InternalState.NEEDS_EMPTYING,
        }
        if state in fast_states or self.detector.cycle.archive_pending:
            return timedelta(seconds=int(APPLIANCE_PRESET["tick_interval_fast_seconds"]))
        return timedelta(seconds=int(APPLIANCE_PRESET["tick_interval_slow_seconds"]))

    def _subscribe_tick(self) -> None:
        @callback
        def _on_tick(now: datetime) -> None:
            self.hass.async_create_task(self._handle_tick(now))

        self._unsubscribers.append(
            async_track_time_interval(
                self.hass,
                _on_tick,
                self._tick_interval(),
            )
        )

    async def _handle_state_change(self, event: Any) -> None:
        await self._process_current_states(event.data.get("time_fired"))
        self.async_set_updated_data(self.data)

    async def _handle_tick(self, now: datetime) -> None:
        async with self._lock:
            if not self.detector:
                return
            result = self.detector.tick(now)
            await self._apply_result(result, now)

    async def _async_update_data(self) -> dict[str, Any]:
        await self._process_current_states()
        return self.data

    async def _process_current_states(self, timestamp: datetime | None = None) -> None:
        async with self._lock:
            if not self.detector:
                return
            now = timestamp or datetime.now(UTC)
            data = self.config
            triggered = self._last_triggered_entity
            self._last_triggered_entity = None

            power_state = self.hass.states.get(data[CONF_POWER_SENSOR])
            energy_state = (
                self.hass.states.get(data[CONF_ENERGY_SENSOR])
                if data.get(CONF_ENERGY_SENSOR)
                else None
            )
            door_state = self.hass.states.get(data[CONF_DOOR_SENSOR])
            movement_state = (
                self.hass.states.get(data[CONF_MOVEMENT_SENSOR])
                if data.get(CONF_MOVEMENT_SENSOR)
                else None
            )
            plug_state = (
                self.hass.states.get(data[CONF_PLUG_SWITCH]) if data.get(CONF_PLUG_SWITCH) else None
            )

            power_available = power_state is not None and power_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            )
            energy_available = (
                (
                    energy_state is not None
                    and energy_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
                )
                if energy_state
                else False
            )
            door_available = door_state is not None and door_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            )
            movement_available = (
                (
                    movement_state is not None
                    and movement_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
                )
                if movement_state
                else False
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
                    data[CONF_MOVEMENT_SENSOR],
                    movement_state.state,
                    now,
                    on_means_true=True,
                )

            plug_on = None
            if plug_state and plug_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                plug_on = plug_state.state == STATE_ON

            source = SampleSource.OTHER
            if triggered == data[CONF_POWER_SENSOR]:
                source = SampleSource.POWER
            elif triggered == data.get(CONF_ENERGY_SENSOR):
                source = SampleSource.ENERGY
            elif triggered == data[CONF_DOOR_SENSOR]:
                source = SampleSource.DOOR
            elif triggered == data.get(CONF_MOVEMENT_SENSOR):
                source = SampleSource.MOVEMENT
            elif triggered == data.get(CONF_PLUG_SWITCH):
                source = SampleSource.PLUG

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
                source=source,
            )

            result = self.detector.process(inp)
            await self._apply_result(result, now)

    async def _apply_result(self, result: Any, now: datetime) -> None:
        self.storage.set_cycle(result.cycle)
        self.storage.add_transitions(result.transitions)

        shadow = self.options.get(OPT_SHADOW_MODE, True)
        for evt in result.events:
            if shadow and evt.name in OPERATIONAL_EVENTS:
                continue
            payload = {**evt.data, "config_entry_id": self.entry.entry_id}
            if shadow:
                payload["shadow"] = True
            self.hass.bus.async_fire(evt.name, payload)

        if result.finalize_archive:
            await self._finalize_archive(result.cycle)

        if self.options.get(OPT_LEGACY_STATUS_MIRROR):
            await self._mirror_legacy_status(result.cycle.public_state)

        if result.cycle.completed_at and result.cycle.started_at:
            duration = (
                datetime.fromisoformat(result.cycle.completed_at.replace("Z", "+00:00"))
                - datetime.fromisoformat(result.cycle.started_at.replace("Z", "+00:00"))
            ).total_seconds()
            if result.cycle.internal_state in (
                InternalState.NEEDS_EMPTYING,
                InternalState.IDLE,
            ):
                self._last_cycle_summary = {
                    "cycle_id": result.cycle.cycle_id,
                    "duration_seconds": int(duration),
                    "energy_wh": result.cycle.accumulated_energy_wh,
                    "program": result.cycle.detected_program,
                }
                self.storage.add_completed_summary(self._last_cycle_summary)

        self.storage.set_normalizer_state(self.normalizer.state.to_dict())
        await self.storage.async_save()

        self.data = {
            "cycle": result.cycle,
            "profiles": self.storage.get_profiles(),
            "training_runs": self.storage.get_training_runs(),
            "latency_stats": self.storage.get_latency_stats(),
            "last_cycle_summary": self._last_cycle_summary,
            "pending_program": self.storage.get_pending_program(),
        }

    async def _finalize_archive(self, cycle: Any) -> None:
        run = self.archive.finalize(
            cycle,
            resample_interval=int(self.options.get(OPT_RESAMPLE_INTERVAL_SECONDS, 15)),
        )
        self.storage.add_training_run(run)
        await self._rebuild_profiles(run.program_id)
        if cycle.calibration_label_consumed:
            self.storage.set_pending_program("auto")
            self.detector.pending_program = "auto"
        self.storage.set_cycle(cycle)
        await self.storage.async_save(immediate=True)

    async def _mirror_legacy_status(self, public_state: str) -> None:
        mapping = {
            "idle": "Empty",
            "starting": "Washing",
            "running": "Washing",
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

    async def _rebuild_profiles(self, program_id: str | None = None) -> None:
        runs = self.storage.get_training_runs()
        profiles = self.storage.get_profiles()
        pids = [program_id] if program_id else list(PROGRAM_CATALOGUE.keys())
        for pid in pids:
            profiles[pid] = build_profile_from_runs(
                pid,
                runs,
                resample_interval_seconds=int(self.options.get(OPT_RESAMPLE_INTERVAL_SECONDS, 15)),
                end_signature_pre_seconds=int(self.options.get("end_signature_pre_seconds", 300)),
                end_signature_post_seconds=int(self.options.get("end_signature_post_seconds", 30)),
            )
        self.storage.set_profiles(profiles)
        if self.detector:
            self.detector.profiles = profiles

    async def async_set_pending_program(self, program: str) -> None:
        """Set pending calibration program for next cycle."""
        self.storage.set_pending_program(program)
        if self.detector:
            self.detector.pending_program = program
        await self.storage.async_save()
        self.async_set_updated_data(self.data)

    async def async_relabel_last_cycle(self, program_id: str) -> None:
        """Relabel the most recent completed training run."""
        runs = self.storage.get_training_runs()
        if not runs:
            raise ValueError("No training runs to relabel")
        run = runs[-1]
        old_program = run.program_id
        run.program_id = program_id
        run.program_name = PROGRAM_CATALOGUE.get(program_id, program_id)
        self.storage.update_training_run(run)
        await self._rebuild_profiles(old_program)
        await self._rebuild_profiles(program_id)
        await self.storage.async_save(immediate=True)
        self.async_set_updated_data(self.data)

    async def async_force_empty(self) -> None:
        """Diagnostic-only: force cycle to empty."""
        if not self.options.get(OPT_ADVANCED_DIAGNOSTICS):
            raise ValueError("force_empty requires advanced_diagnostics option")
        if self.detector:
            result = self.detector.force_empty()
            await self._apply_result(result, datetime.now(UTC))
            self.async_set_updated_data(self.data)
