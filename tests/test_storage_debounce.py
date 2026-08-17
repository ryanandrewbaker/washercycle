"""Regression tests for WasherCycle storage debounce lifecycle."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.core import CoreState, HomeAssistant

from custom_components.washercycle.coordinator import WasherCycleCoordinator
from custom_components.washercycle.storage import WasherCycleStorage
from tests.helpers.ha_installed import home_assistant_installed

pytestmark = pytest.mark.skipif(
    not home_assistant_installed(),
    reason="Home Assistant is not installed",
)


def _washercycle_delayed_save_tasks() -> list[asyncio.Task[Any]]:
    """Return pending WasherCycle-owned _delayed_save tasks, if any."""
    return [
        task
        for task in asyncio.all_tasks()
        if not task.done()
        and task.get_coro() is not None
        and "_delayed_save" in task.get_coro().__qualname__
        and "WasherCycleStorage" in task.get_coro().__qualname__
    ]


@pytest.mark.asyncio
async def test_debounced_save_uses_store_delay_not_washercycle_task(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Debounced saves schedule Home Assistant Store delay handles only."""
    monkeypatch.setattr(
        "custom_components.washercycle.storage._SAVE_DEBOUNCE_SECONDS",
        30,
    )
    storage = WasherCycleStorage(hass, "debounce-task-test")
    await storage.async_load()

    await storage.async_save()

    assert _washercycle_delayed_save_tasks() == []
    assert storage._store._delay_handle is not None


@pytest.mark.asyncio
async def test_multiple_debounced_saves_coalesce_to_latest_data(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated debounced saves within the window persist the latest payload."""
    monkeypatch.setattr(
        "custom_components.washercycle.storage._SAVE_DEBOUNCE_SECONDS",
        0.05,
    )
    entry_id = "debounce-coalesce"
    storage = WasherCycleStorage(hass, entry_id)
    await storage.async_load()

    storage.set_pending_program("quick_wash")
    await storage.async_save()
    storage.set_pending_program("daily_wash")
    await storage.async_save()
    storage.set_pending_program("bedding")
    await storage.async_save()

    await asyncio.sleep(0.1)
    await hass.async_block_till_done()

    reloaded = WasherCycleStorage(hass, entry_id)
    loaded = await reloaded.async_load()
    assert loaded["pending_program"] == "bedding"


@pytest.mark.asyncio
async def test_save_now_flushes_pending_debounce_without_washercycle_task(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Immediate save writes latest data and leaves no WasherCycle debounce task."""
    monkeypatch.setattr(
        "custom_components.washercycle.storage._SAVE_DEBOUNCE_SECONDS",
        30,
    )
    entry_id = "debounce-immediate"
    storage = WasherCycleStorage(hass, entry_id)
    await storage.async_load()

    storage.set_pending_program("daily_wash")
    await storage.async_save()
    assert storage._store._delay_handle is not None

    storage.set_pending_program("bedding")
    await storage.async_save_now()
    await hass.async_block_till_done()

    assert _washercycle_delayed_save_tasks() == []
    assert storage._store._delay_handle is None

    reloaded = WasherCycleStorage(hass, entry_id)
    loaded = await reloaded.async_load()
    assert loaded["pending_program"] == "bedding"


@pytest.mark.asyncio
async def test_coordinator_shutdown_with_pending_debounced_save(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator shutdown flushes pending debounced storage without lingering tasks."""
    monkeypatch.setattr(
        "custom_components.washercycle.storage._SAVE_DEBOUNCE_SECONDS",
        30,
    )
    monkeypatch.setattr(
        "custom_components.washercycle.coordinator.WasherCycleCoordinator._subscribe_tick",
        lambda self: None,
    )
    monkeypatch.setattr(
        "custom_components.washercycle.coordinator.WasherCycleCoordinator._subscribe_sources",
        lambda self: None,
    )

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.washercycle.const import (
        CONF_DOOR_SENSOR,
        CONF_ENERGY_SENSOR,
        CONF_POWER_SENSOR,
        DOMAIN,
    )

    entry_id = "coordinator-shutdown"
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        title="WasherCycle",
        data={
            CONF_POWER_SENSOR: "sensor.washer_power",
            CONF_ENERGY_SENSOR: "sensor.washer_energy",
            CONF_DOOR_SENSOR: "binary_sensor.washer_door",
        },
        options={"shadow_mode": True},
    )
    entry.add_to_hass(hass)

    coordinator = WasherCycleCoordinator(hass, entry)
    await coordinator.async_setup()
    coordinator.storage.set_pending_program("bedding")
    await coordinator.storage.async_save()
    assert coordinator.storage._store._delay_handle is not None

    await coordinator.async_shutdown()
    await hass.async_block_till_done()

    assert _washercycle_delayed_save_tasks() == []
    assert coordinator.storage._store._delay_handle is None

    reloaded = WasherCycleStorage(hass, entry_id)
    loaded = await reloaded.async_load()
    assert loaded["pending_program"] == "bedding"


@pytest.mark.asyncio
async def test_final_write_flushes_pending_store_delay(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Home Assistant final-write event flushes pending Store debounced data."""
    monkeypatch.setattr(
        "custom_components.washercycle.storage._SAVE_DEBOUNCE_SECONDS",
        30,
    )
    entry_id = "final-write"
    storage = WasherCycleStorage(hass, entry_id)
    await storage.async_load()
    storage.set_pending_program("drum_clean")
    await storage.async_save()

    hass.set_state(CoreState.stopping)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
    await hass.async_block_till_done()

    assert _washercycle_delayed_save_tasks() == []
    assert storage._store._delay_handle is None

    reloaded = WasherCycleStorage(hass, entry_id)
    loaded = await reloaded.async_load()
    assert loaded["pending_program"] == "drum_clean"
