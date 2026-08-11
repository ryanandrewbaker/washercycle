"""Entity registry cleanup for WasherCycle."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORTED_UNIQUE_ID_SUFFIXES = frozenset(
    {
        "state",
        "program",
        "progress",
        "time_remaining",
        "expected_completion",
        "last_cycle_duration",
        "last_cycle_energy",
        "program_confidence",
        "eta_confidence",
        "running",
        "needs_emptying",
        "program_select",
    }
)


async def async_remove_obsolete_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove WasherCycle entity registry entries that are no longer supported."""
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity_entry.domain != DOMAIN:
            continue
        unique_id = entity_entry.unique_id or ""
        if not unique_id.startswith(prefix):
            continue
        suffix = unique_id[len(prefix) :]
        if suffix in SUPPORTED_UNIQUE_ID_SUFFIXES:
            continue
        _LOGGER.info(
            "Removing obsolete WasherCycle entity %s (unique_id=%s)",
            entity_entry.entity_id,
            unique_id,
        )
        registry.async_remove(entity_entry.entity_id)
