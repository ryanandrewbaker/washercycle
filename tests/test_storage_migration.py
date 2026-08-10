"""Storage migration tests."""

from __future__ import annotations

import copy

from custom_components.washercycle.const import STORAGE_KEY, STORAGE_VERSION
from custom_components.washercycle.storage import migrate_storage_payload
from tests.helpers.v1_storage import sample_v1_storage_payload


def test_migrate_v1_to_v2_removes_announcement_state():
    data = sample_v1_storage_payload("test_entry")
    migrated = migrate_storage_payload(1, data)
    assert migrated["version"] == STORAGE_VERSION
    assert "announcement_state" not in migrated
    assert "manual_timing" in migrated["training_runs"][0].get("anomaly_flags", [])


def test_migrate_v1_does_not_mutate_source_payload():
    data = sample_v1_storage_payload("test_entry")
    original = copy.deepcopy(data)
    migrate_storage_payload(1, data)
    assert data == original


def test_migrate_v2_is_idempotent():
    data = sample_v1_storage_payload("test_entry")
    first = migrate_storage_payload(1, data)
    second = migrate_storage_payload(STORAGE_VERSION, first)
    assert second == first


def test_migrate_v1_preserves_core_user_data():
    entry_id = "entry-abc"
    data = sample_v1_storage_payload(entry_id)
    migrated = migrate_storage_payload(1, data)
    assert migrated["config_entry_id"] == entry_id
    assert migrated["pending_program"] == "quick_wash"
    assert migrated["current_cycle"]["cycle_id"] == "cycle-live"
    assert migrated["training_runs"][0]["run_id"] == "run-calibration-1"
    assert migrated["profiles"]["daily_wash"]["duration_median_seconds"] == 5400.0
    assert migrated["completed_history"][0]["cycle_id"] == "cycle-old"
    assert migrated["profiles"]["daily_wash"]["recognition_ready"] is False
    assert migrated["profiles"]["daily_wash"]["profile_schema_version"] == 2
    assert migrated["training_runs"][0]["schema_version"] == 2


def test_storage_key_format_unchanged():
    entry_id = "my-entry"
    assert f"{STORAGE_KEY}_{entry_id}" == "washercycle.storage_my-entry"
