"""Persistent storage for WasherCycle."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import (
    ActiveRecording,
    CycleRecord,
    LatencyStats,
    ProgramProfile,
    TrainingRun,
)
from .profiles import seed_profiles

_LOGGER = logging.getLogger(__name__)


class WasherCycleStorage:
    """Versioned storage with debounced writes."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{entry_id}",
        )
        self._save_task: asyncio.Task | None = None
        self._data: dict[str, Any] = {}

    async def async_load(self) -> dict[str, Any]:
        """Load storage data."""
        stored = await self._store.async_load()
        if stored is None:
            self._data = self._default_data()
        else:
            self._data = self._migrate(stored)
        return self._data

    async def async_save(self, *, immediate: bool = False) -> None:
        """Save storage data, debounced unless immediate."""
        if immediate:
            await self._store.async_save(self._data)
            return

        if self._save_task and not self._save_task.done():
            self._save_task.cancel()

        async def _delayed_save() -> None:
            await asyncio.sleep(30)
            await self._store.async_save(self._data)

        self._save_task = self.hass.async_create_task(_delayed_save())

    async def async_save_now(self) -> None:
        """Save immediately."""
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        await self._store.async_save(self._data)

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def get_cycle(self) -> CycleRecord:
        """Get current cycle record."""
        cycle_data = self._data.get("current_cycle")
        if cycle_data:
            return CycleRecord.from_dict(cycle_data)
        return CycleRecord(cycle_id="")

    def set_cycle(self, cycle: CycleRecord) -> None:
        """Update current cycle."""
        self._data["current_cycle"] = cycle.to_dict()

    def get_recording(self) -> ActiveRecording:
        """Get active recording."""
        rec_data = self._data.get("active_recording")
        if rec_data:
            return ActiveRecording.from_dict(rec_data)
        return ActiveRecording()

    def set_recording(self, recording: ActiveRecording) -> None:
        """Update active recording."""
        self._data["active_recording"] = recording.to_dict()

    def get_profiles(self) -> dict[str, ProgramProfile]:
        """Get program profiles."""
        profiles_data = self._data.get("profiles", {})
        return {
            pid: ProgramProfile.from_dict(pdata)
            for pid, pdata in profiles_data.items()
        }

    def set_profiles(self, profiles: dict[str, ProgramProfile]) -> None:
        """Update program profiles."""
        self._data["profiles"] = {pid: p.to_dict() for pid, p in profiles.items()}

    def get_training_runs(self) -> list[TrainingRun]:
        """Get all training runs."""
        return [
            TrainingRun.from_dict(r) for r in self._data.get("training_runs", [])
        ]

    def add_training_run(self, run: TrainingRun) -> None:
        """Add a training run with retention limit."""
        runs = self.get_training_runs()
        runs.append(run)
        retention = self._data.get("raw_run_retention", 50)
        if len(runs) > retention:
            runs = runs[-retention:]
        self._data["training_runs"] = [r.to_dict() for r in runs]

    def get_training_run(self, run_id: str) -> TrainingRun | None:
        """Get a specific training run."""
        for run in self.get_training_runs():
            if run.run_id == run_id:
                return run
        return None

    def update_training_run(self, run: TrainingRun) -> None:
        """Update an existing training run."""
        runs = self.get_training_runs()
        self._data["training_runs"] = [
            run.to_dict() if r.run_id == run.run_id else r.to_dict() for r in runs
        ]

    def delete_training_run(self, run_id: str) -> bool:
        """Delete a training run."""
        runs = self.get_training_runs()
        new_runs = [r for r in runs if r.run_id != run_id]
        if len(new_runs) == len(runs):
            return False
        self._data["training_runs"] = [r.to_dict() for r in new_runs]
        return True

    def get_latency_stats(self) -> LatencyStats:
        """Get latency statistics."""
        data = self._data.get("latency_stats", {})
        return LatencyStats.from_dict(data)

    def set_latency_stats(self, stats: LatencyStats) -> None:
        """Update latency statistics."""
        self._data["latency_stats"] = stats.to_dict()

    def get_completed_history(self) -> list[dict[str, Any]]:
        """Get completed cycle summaries."""
        return list(self._data.get("completed_history", []))

    def add_completed_summary(self, summary: dict[str, Any]) -> None:
        """Add completed cycle summary."""
        history = self.get_completed_history()
        history.append(summary)
        retention = self._data.get("completed_history_retention", 20)
        if len(history) > retention:
            history = history[-retention:]
        self._data["completed_history"] = history

    def get_pending_program(self) -> str:
        """Get pending manual program selection."""
        return self._data.get("pending_program", "auto")

    def set_pending_program(self, program: str) -> None:
        """Set pending manual program."""
        self._data["pending_program"] = program

    def get_announcement_state(self) -> dict[str, Any]:
        """Get announcement delivery state."""
        return dict(self._data.get("announcement_state", {}))

    def set_announcement_state(self, state: dict[str, Any]) -> None:
        """Update announcement delivery state."""
        self._data["announcement_state"] = state

    def get_normalizer_state(self) -> dict[str, Any]:
        """Get normalizer state."""
        return dict(self._data.get("normalizer_state", {}))

    def set_normalizer_state(self, state: dict[str, Any]) -> None:
        """Update normalizer state."""
        self._data["normalizer_state"] = state

    def get_transitions(self) -> list[dict[str, Any]]:
        """Get recent state transitions."""
        return list(self._data.get("recent_transitions", []))[-50:]

    def add_transitions(self, transitions: list) -> None:
        """Add state transitions."""
        existing = self.get_transitions()
        for t in transitions:
            existing.append(
                {
                    "timestamp": t.timestamp,
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "reason": t.reason,
                }
            )
        self._data["recent_transitions"] = existing[-50:]

    def get_data_quality_counters(self) -> dict[str, int]:
        """Get data quality counters."""
        return dict(self._data.get("data_quality_counters", {}))

    def increment_quality_counter(self, key: str) -> None:
        """Increment a data quality counter."""
        counters = self.get_data_quality_counters()
        counters[key] = counters.get(key, 0) + 1
        self._data["data_quality_counters"] = counters

    def _default_data(self) -> dict[str, Any]:
        profiles = seed_profiles()
        return {
            "version": STORAGE_VERSION,
            "config_entry_id": self.entry_id,
            "current_cycle": CycleRecord(cycle_id="").to_dict(),
            "active_recording": ActiveRecording().to_dict(),
            "profiles": {pid: p.to_dict() for pid, p in profiles.items()},
            "training_runs": [],
            "completed_history": [],
            "latency_stats": LatencyStats().to_dict(),
            "pending_program": "auto",
            "announcement_state": {},
            "normalizer_state": {},
            "recent_transitions": [],
            "data_quality_counters": {},
            "raw_run_retention": 50,
            "completed_history_retention": 20,
        }

    def _migrate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate storage data to current version."""
        version = data.get("version", 1)
        if version < STORAGE_VERSION:
            _LOGGER.info("Migrating WasherCycle storage from v%s to v%s", version, STORAGE_VERSION)
            data["version"] = STORAGE_VERSION
        if "profiles" not in data:
            profiles = seed_profiles()
            data["profiles"] = {pid: p.to_dict() for pid, p in profiles.items()}
        return data
