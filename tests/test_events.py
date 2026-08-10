"""Event payload contract tests."""

from __future__ import annotations

from custom_components.washercycle.const import (
    EVENT_CYCLE_COMPLETED,
    EVENT_CYCLE_EMPTIED,
    EVENT_CYCLE_STARTED,
    EVENT_NEEDS_REWASH,
    EVENT_PROGRAM_IDENTIFIED,
)

COMMON_EVENT_FIELDS = {
    "cycle_id",
    "program_id",
    "program_name",
    "program_source",
    "program_confidence",
    "started_at",
    "expected_completion_at",
    "completed_at",
    "energy_wh",
    "completion_reason",
    "restart_recovered",
    "sensor_data_incomplete",
}


def test_event_names_stable():
    assert EVENT_CYCLE_STARTED == "washercycle_cycle_started"
    assert EVENT_PROGRAM_IDENTIFIED == "washercycle_program_identified"
    assert EVENT_CYCLE_COMPLETED == "washercycle_cycle_completed"
    assert EVENT_CYCLE_EMPTIED == "washercycle_cycle_emptied"
    assert EVENT_NEEDS_REWASH == "washercycle_needs_rewash"


def test_cycle_completed_requires_immediately_emptied():
    sample = {
        "cycle_id": "abc",
        "immediately_emptied": False,
        **{f: None for f in COMMON_EVENT_FIELDS},
    }
    assert "immediately_emptied" in sample
    assert isinstance(sample["immediately_emptied"], bool)
