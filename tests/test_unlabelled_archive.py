"""Unlabelled archive tests."""

from __future__ import annotations

from custom_components.washercycle.cycle_archive import UNKNOWN_PROGRAM_ID, resolve_archive_program
from custom_components.washercycle.models import CycleRecord, ProgramMatchState


def test_auto_without_confident_match_archives_as_unknown():
    cycle = CycleRecord(
        cycle_id="c1",
        selected_program="auto",
        detected_program=None,
        program_match_state=ProgramMatchState.TENTATIVE,
    )
    program_id, included, flags = resolve_archive_program(cycle)
    assert program_id == UNKNOWN_PROGRAM_ID
    assert included is False
    assert "unlabelled_program" in flags


def test_confident_auto_match_is_included():
    cycle = CycleRecord(
        cycle_id="c2",
        selected_program="auto",
        detected_program="daily_wash",
        program_match_state=ProgramMatchState.CONFIDENT,
    )
    program_id, included, flags = resolve_archive_program(cycle)
    assert program_id == "daily_wash"
    assert included is True
    assert flags == []
