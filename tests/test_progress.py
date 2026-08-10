"""Tests for progress calculation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.washercycle.models import EtaConfidence, ProgramMatchState, ProgramProfile
from custom_components.washercycle.progress import compute_progress


def test_progress_monotonic():
    started = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    profile = ProgramProfile(
        program_id="daily_wash",
        display_name="Daily Wash",
        duration_median_seconds=3600,
        duration_mad_seconds=300,
    )
    p1, _, _, _ = compute_progress(
        started_at=started.isoformat(),
        now=started + timedelta(minutes=10),
        profile=profile,
        program_match_state=ProgramMatchState.CONFIDENT,
        current_progress=0.0,
    )
    p2, _, _, _ = compute_progress(
        started_at=started.isoformat(),
        now=started + timedelta(minutes=5),
        profile=profile,
        program_match_state=ProgramMatchState.CONFIDENT,
        current_progress=p1,
    )
    assert p2 >= p1


def test_progress_never_reaches_100_before_completion():
    started = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    profile = ProgramProfile(
        program_id="daily_wash",
        display_name="Daily Wash",
        duration_median_seconds=3600,
    )
    progress, _, _, _ = compute_progress(
        started_at=started.isoformat(),
        now=started + timedelta(hours=2),
        profile=profile,
        program_match_state=ProgramMatchState.CONFIDENT,
        internal_state="RUNNING",
    )
    assert progress < 100


def test_eta_uses_started_at_plus_duration_not_arbitrary_extension():
    started = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    profile = ProgramProfile(
        program_id="daily_wash",
        display_name="Daily Wash",
        duration_median_seconds=3600,
        duration_mad_seconds=300,
    )
    now = started + timedelta(minutes=30)
    _, remaining, expected, conf = compute_progress(
        started_at=started.isoformat(),
        now=now,
        profile=profile,
        program_match_state=ProgramMatchState.CONFIDENT,
    )
    assert conf == EtaConfidence.MATCHED
    assert expected == started + timedelta(seconds=3600)
    assert remaining == 1800
