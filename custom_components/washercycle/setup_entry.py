"""Home Assistant setup helpers for WasherCycle."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr

from .const import (
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    PLATFORMS,
    SERVICE_DELETE_RUN,
    SERVICE_EXCLUDE_RUN,
    SERVICE_FORCE_EMPTY,
    SERVICE_INCLUDE_RUN,
    SERVICE_REBUILD_PROFILES,
    SERVICE_RELABEL_LAST_CYCLE,
)
from .coordinator import WasherCycleCoordinator
from .entity_registry import async_remove_obsolete_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WasherCycle from config entry."""
    coordinator = WasherCycleCoordinator(hass, entry)
    await coordinator.async_setup()

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=DEFAULT_DEVICE_NAME,
        manufacturer=MANUFACTURER,
        model=MODEL,
    )
    coordinator.device_info = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": DEFAULT_DEVICE_NAME,
        "manufacturer": MANUFACTURER,
        "model": MODEL,
    }

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_remove_obsolete_entities(hass, entry)
    _register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload WasherCycle."""
    coordinator: WasherCycleCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload WasherCycle."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete WasherCycle storage when the config entry is removed."""
    from .storage import WasherCycleStorage

    storage = WasherCycleStorage(hass, entry.entry_id)
    await storage.async_remove()


def _register_services(hass: HomeAssistant) -> None:
    """Register WasherCycle services."""

    async def _get_coordinator(call: ServiceCall) -> WasherCycleCoordinator | None:
        entry_id = call.data.get("config_entry_id")
        if entry_id and entry_id in hass.data.get(DOMAIN, {}):
            return hass.data[DOMAIN][entry_id]
        domain_data = hass.data.get(DOMAIN, {})
        if len(domain_data) == 1:
            return next(iter(domain_data.values()))
        return None

    async def handle_relabel_last_cycle(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        if coordinator and (program_id := call.data.get("program_id")):
            await coordinator.async_relabel_last_cycle(program_id)

    async def handle_force_empty(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        if coordinator:
            await coordinator.async_force_empty()

    async def handle_rebuild_profiles(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        if coordinator:
            await coordinator._rebuild_profiles(call.data.get("program_id"))

    async def handle_exclude_run(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        if coordinator and (run_id := call.data.get("run_id")):
            run = coordinator.storage.get_training_run(run_id)
            if run:
                run.included_in_profile = False
                coordinator.storage.update_training_run(run)
                await coordinator._rebuild_profiles(run.program_id)
                await coordinator.storage.async_save(immediate=True)

    async def handle_include_run(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        if coordinator and (run_id := call.data.get("run_id")):
            run = coordinator.storage.get_training_run(run_id)
            if run:
                run.included_in_profile = True
                coordinator.storage.update_training_run(run)
                await coordinator._rebuild_profiles(run.program_id)
                await coordinator.storage.async_save(immediate=True)

    async def handle_delete_run(call: ServiceCall) -> None:
        if not call.data.get("confirm"):
            return
        coordinator = await _get_coordinator(call)
        if coordinator and (run_id := call.data.get("run_id")):
            run = coordinator.storage.get_training_run(run_id)
            if run:
                coordinator.storage.delete_training_run(run_id)
                await coordinator._rebuild_profiles(run.program_id)
                await coordinator.storage.async_save(immediate=True)

    service_schema = vol.Schema(
        {
            vol.Optional("config_entry_id"): str,
            vol.Optional("program_id"): str,
            vol.Optional("run_id"): str,
            vol.Optional("confirm"): bool,
        }
    )

    services = {
        SERVICE_RELABEL_LAST_CYCLE: handle_relabel_last_cycle,
        SERVICE_FORCE_EMPTY: handle_force_empty,
        SERVICE_REBUILD_PROFILES: handle_rebuild_profiles,
        SERVICE_EXCLUDE_RUN: handle_exclude_run,
        SERVICE_INCLUDE_RUN: handle_include_run,
        SERVICE_DELETE_RUN: handle_delete_run,
    }

    for service, handler in services.items():
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(DOMAIN, service, handler, schema=service_schema)
