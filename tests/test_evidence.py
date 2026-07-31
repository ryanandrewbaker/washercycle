"""Tests for evidence scoring."""

from __future__ import annotations

from datetime import datetime, timezone

from custom_components.washercycle.evidence import score_completion_evidence
from custom_components.washercycle.models import DetectorConfig, ProgramProfile


def test_standby_power_scores_high():
    config = DetectorConfig()
    profile = ProgramProfile(
        program_id="daily_wash",
        display_name="Daily Wash",
        duration_median_seconds=3600,
        duration_mad_seconds=300,
        earliest_plausible_completion_seconds=2000,
        mean_power_median_w=50,
    )
    score = score_completion_evidence(
        now=datetime(2026, 7, 31, 11, 0, tzinfo=timezone.utc),
        elapsed_seconds=3700,
        current_power_w=3.0,
        movement_active=False,
        energy_wh=500,
        energy_stable=True,
        trace=[],
        profile=profile,
        config=config,
    )
    assert score.standby_power > 0.5
    assert score.total > 0


def test_contradictory_power_resumed():
    config = DetectorConfig()
    score = score_completion_evidence(
        now=datetime(2026, 7, 31, 11, 0, tzinfo=timezone.utc),
        elapsed_seconds=3700,
        current_power_w=100.0,
        movement_active=True,
        energy_wh=500,
        energy_stable=False,
        trace=[],
        profile=None,
        config=config,
    )
    assert score.contradictory is True
