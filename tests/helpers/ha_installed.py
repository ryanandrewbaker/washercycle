"""Detect whether the real Home Assistant package is available for integration tests."""

from __future__ import annotations


def home_assistant_installed() -> bool:
    """Return True when the real Home Assistant test harness can be used."""
    try:
        from homeassistant.helpers.storage import Store

        return hasattr(Store, "_async_migrate_func")
    except ImportError:
        return False
