"""Entity registry cleanup tests."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.washercycle.const import DOMAIN
from custom_components.washercycle.entity_registry import async_remove_obsolete_entities
from tests.helpers.ha_installed import home_assistant_installed

pytestmark = pytest.mark.skipif(
    not home_assistant_installed(),
    reason="Home Assistant is not installed",
)


@pytest.mark.asyncio
async def test_obsolete_entities_removed(hass: HomeAssistant) -> None:
    entry_id = "registry-cleanup"
    entry = MockConfigEntry(domain=DOMAIN, entry_id=entry_id, title="WasherCycle")
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        domain=DOMAIN,
        platform="button",
        unique_id=f"{entry_id}_start_recording",
        suggested_object_id="washercycle_start_recording",
        config_entry=entry,
    )
    registry.async_get_or_create(
        domain=DOMAIN,
        platform="sensor",
        unique_id=f"{entry_id}_state",
        suggested_object_id="washercycle_state",
        config_entry=entry,
    )

    await async_remove_obsolete_entities(hass, entry)

    remaining = er.async_entries_for_config_entry(registry, entry.entry_id)
    unique_ids = {entity.unique_id for entity in remaining}
    assert f"{entry_id}_start_recording" not in unique_ids
    assert f"{entry_id}_state" in unique_ids
