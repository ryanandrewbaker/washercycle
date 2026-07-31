"""Tests for progress calculation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.washercycle.models import ProgramMatchState, ProgramProfile
from custom_components.washercycle.progress import compute_progress


def test_progress_monotonic():
    profile = ProgramProfile(
        program_id="daily_wash",
        display_name="Daily Wash",
        duration_median_seconds=3600,
        duration_mad_seconds=300,
    )
    start = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    p1, _, _, _ = compute_progress(
        started_at=start.isoformat(),
        now=start + timedelta(seconds=600),
        profile=profile,
        program_match_state=ProgramMatchState.CONFIDENT,
        current_progress=0,
    )
    p2, _, _, _ = compute_progress(
        started_at=start.isoformat(),
        now=start + timedelta(seconds=1200),
        profile=profile,
        program_match_state=ProgramMatchState.CONFIDENT,
        current_progress=p1,
    )
    assert p2 >= p1


def test_unknown_eta_before_match():
    progress, remaining, expected, eta = compute_progress(
        started_at=None,
        now=datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc),
        profile=None,
        program_match_state=ProgramMatchState.UNKNOWN,
    )
    assert eta == "unknown"
