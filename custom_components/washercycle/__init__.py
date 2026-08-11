"""WasherCycle integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

__all__ = [
    "DOMAIN",
    "async_setup",
    "async_setup_entry",
    "async_unload_entry",
    "async_reload_entry",
    "async_remove_entry",
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up WasherCycle."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WasherCycle from config entry."""
    from . import setup_entry as _setup

    return await _setup.async_setup_entry(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload WasherCycle."""
    from . import setup_entry as _setup

    return await _setup.async_unload_entry(hass, entry)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload WasherCycle."""
    from . import setup_entry as _setup

    await _setup.async_reload_entry(hass, entry)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove WasherCycle storage when the config entry is deleted."""
    from . import setup_entry as _setup

    await _setup.async_remove_entry(hass, entry)
