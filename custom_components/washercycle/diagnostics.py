"""Diagnostics for WasherCycle."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return await async_get_diagnostics(hass, entry)


async def async_get_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Build diagnostics snapshot."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    cycle = coordinator.detector.cycle if coordinator.detector else None

    profiles = coordinator.storage.get_profiles()
    profile_summary = {
        pid: {
            "confirmed_run_count": p.confirmed_run_count,
            "real_run_count": p.real_run_count,
            "recognition_ready": p.recognition_ready,
            "duration_median_seconds": p.duration_median_seconds,
            "last_rebuilt_at": p.last_rebuilt_at,
        }
        for pid, p in profiles.items()
    }

    return {
        "version": entry.version if hasattr(entry, "version") else None,
        "config": entry.data,
        "options": entry.options,
        "detector_state": cycle.internal_state if cycle else None,
        "public_state": cycle.public_state if cycle else None,
        "state_reason": cycle.state_reason if cycle else None,
        "archive_pending": cycle.archive_pending if cycle else None,
        "pending_program": coordinator.storage.get_pending_program(),
        "program_confidence": cycle.program_confidence if cycle else None,
        "eta_confidence": cycle.eta_confidence if cycle else None,
        "profile_summary": profile_summary,
        "training_run_count": len(coordinator.storage.get_training_runs()),
        "latency_stats": coordinator.storage.get_latency_stats().to_dict(),
        "data_quality_counters": coordinator.storage.get_data_quality_counters(),
        "recent_transitions": coordinator.storage.get_transitions(),
        "last_cycle_summary": coordinator.data.get("last_cycle_summary", {}),
        "rejected_samples": [
            {"entity": r.entity, "reason": r.reason}
            for r in coordinator.normalizer.state.rejected[-20:]
        ],
    }
