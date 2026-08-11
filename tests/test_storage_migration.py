"""Storage migration tests."""

from __future__ import annotations

import copy

from custom_components.washercycle.const import STORAGE_KEY, STORAGE_VERSION
from custom_components.washercycle.storage import migrate_storage_payload
from tests.helpers.v1_storage import sample_v1_storage_payload, sample_v2_storage_payload


def test_migrate_v1_to_v3_removes_obsolete_keys_and_resets_learning_data():
    data = sample_v1_storage_payload("test_entry")
    migrated = migrate_storage_payload(1, data)
    assert migrated["version"] == STORAGE_VERSION
    assert "announcement_state" not in migrated
    assert "active_recording" not in migrated
    assert migrated["pending_program"] == "auto"
    assert migrated["training_runs"] == []
    assert migrated["completed_history"] == []
    assert migrated["current_cycle"]["cycle_id"] == ""


def test_migrate_v2_to_v3_resets_learning_data():
    data = sample_v2_storage_payload("test_entry")
    migrated = migrate_storage_payload(2, data)
    assert migrated["version"] == STORAGE_VERSION
    assert migrated["pending_program"] == "auto"
    assert migrated["training_runs"] == []
    assert migrated["completed_history"] == []
    assert migrated["current_cycle"]["cycle_id"] == ""


def test_migrate_v1_does_not_mutate_source_payload():
    data = sample_v1_storage_payload("test_entry")
    original = copy.deepcopy(data)
    migrate_storage_payload(1, data)
    assert data == original


def test_migrate_v3_is_idempotent():
    data = sample_v1_storage_payload("test_entry")
    first = migrate_storage_payload(1, data)
    second = migrate_storage_payload(STORAGE_VERSION, first)
    assert second == first


def test_migrate_v1_preserves_config_entry_id():
    entry_id = "entry-abc"
    data = sample_v1_storage_payload(entry_id)
    migrated = migrate_storage_payload(1, data)
    assert migrated["config_entry_id"] == entry_id


def test_storage_key_format_unchanged():
    entry_id = "my-entry"
    assert f"{STORAGE_KEY}_{entry_id}" == "washercycle.storage_my-entry"
