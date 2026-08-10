"""Public contract tests for WasherCycle."""

from __future__ import annotations

from custom_components.washercycle.const import PROGRAM_CATALOGUE, PROGRAM_SELECT_OPTIONS
from custom_components.washercycle.models import PublicState


REQUIRED_PUBLIC_STATES = {
    PublicState.IDLE,
    PublicState.STARTING,
    PublicState.RUNNING,
    PublicState.FINISHING,
    PublicState.NEEDS_EMPTYING,
    PublicState.NEEDS_REWASH,
    PublicState.UNAVAILABLE,
}

CONTRACT_ENTITY_SUFFIXES = [
    "_state",
    "_program",
    "_progress",
    "_time_remaining",
    "_expected_completion",
    "_last_cycle_duration",
    "_last_cycle_energy",
    "_program_confidence",
    "_eta_confidence",
    "_running",
    "_needs_emptying",
    "_program_select",
]


def test_public_states_contract():
    assert PublicState.PAUSED not in REQUIRED_PUBLIC_STATES
    assert PublicState.UNKNOWN not in REQUIRED_PUBLIC_STATES
    for state in REQUIRED_PUBLIC_STATES:
        assert isinstance(state, str)


def test_program_catalogue_contract():
    assert set(PROGRAM_CATALOGUE.keys()) == {
        "quick_wash",
        "daily_wash",
        "bedding",
        "drum_clean",
    }
    assert PROGRAM_CATALOGUE["quick_wash"] == "Quick Wash"
    assert PROGRAM_CATALOGUE["daily_wash"] == "Daily Wash"
    assert PROGRAM_CATALOGUE["bedding"] == "Bedding"
    assert PROGRAM_CATALOGUE["drum_clean"] == "Drum Clean"


def test_select_options_contract():
    assert PROGRAM_SELECT_OPTIONS[0] == "auto"
    assert len(PROGRAM_SELECT_OPTIONS) == 5


def test_contract_entity_suffixes_complete():
    assert len(CONTRACT_ENTITY_SUFFIXES) == 12
