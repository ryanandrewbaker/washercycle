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
    SERVICE_CANCEL_RECORDING,
    SERVICE_DELETE_RUN,
    SERVICE_EXCLUDE_RUN,
    SERVICE_FORCE_EMPTY,
    SERVICE_INCLUDE_RUN,
    SERVICE_MARK_COMPLETE,
    SERVICE_REBUILD_PROFILES,
    SERVICE_START_RECORDING,
)
from .coordinator import WasherCycleCoordinator

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

    async def handle_start_recording(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        if coordinator:
            await coordinator.async_start_recording(call.data.get("program_id"))

    async def handle_mark_complete(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        if coordinator:
            await coordinator.async_mark_complete()

    async def handle_cancel_recording(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        if coordinator:
            await coordinator.async_cancel_recording()

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
        SERVICE_START_RECORDING: handle_start_recording,
        SERVICE_MARK_COMPLETE: handle_mark_complete,
        SERVICE_CANCEL_RECORDING: handle_cancel_recording,
        SERVICE_FORCE_EMPTY: handle_force_empty,
        SERVICE_REBUILD_PROFILES: handle_rebuild_profiles,
        SERVICE_EXCLUDE_RUN: handle_exclude_run,
        SERVICE_INCLUDE_RUN: handle_include_run,
        SERVICE_DELETE_RUN: handle_delete_run,
    }

    for service, handler in services.items():
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(DOMAIN, service, handler, schema=service_schema)
