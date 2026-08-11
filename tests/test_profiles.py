"""Tests for program profiles."""

from __future__ import annotations

from custom_components.washercycle.models import TrainingRun
from custom_components.washercycle.profiles import build_profile_from_runs, seed_profiles
from custom_components.washercycle.stats import mad, median


def test_median_and_mad():
    assert median([1, 2, 3, 4, 100]) == 3
    assert mad([1, 2, 3, 4, 100], 3) < 2


def test_one_run_creates_provisional_profile():
    run = TrainingRun(
        run_id="r1",
        program_id="daily_wash",
        program_name="Daily Wash",
        user_start_at="2026-01-01T10:00:00+00:00",
        user_complete_at="2026-01-01T11:00:00+00:00",
        observed_duration_seconds=3600,
        raw={"power": [{"t": "2026-01-01T10:00:00+00:00", "w": 100}]},
        derived={"cycle_energy_wh": 500, "peak_power_w": 800, "mean_power_w": 200},
    )
    profile = build_profile_from_runs("daily_wash", [run])
    assert profile.confirmed_run_count == 1
    assert profile.duration_median_seconds == 3600


def test_outlier_does_not_distort_median():
    runs = []
    for i, dur in enumerate([3600, 3650, 3700, 10000]):
        runs.append(
            TrainingRun(
                run_id=f"r{i}",
                program_id="daily_wash",
                program_name="Daily Wash",
                user_start_at="2026-01-01T10:00:00+00:00",
                user_complete_at="2026-01-01T11:00:00+00:00",
                observed_duration_seconds=dur,
                raw={"power": []},
                derived={"cycle_energy_wh": 500, "peak_power_w": 800, "mean_power_w": 200},
            )
        )
    profile = build_profile_from_runs("daily_wash", runs)
    assert profile.duration_median_seconds < 4000


def test_seed_profiles():
    profiles = seed_profiles()
    assert "daily_wash" in profiles
    assert "drum_clean" in profiles


def test_unlabelled_program_excluded_from_real_run_count():
    runs = [
        TrainingRun(
            run_id="u1",
            program_id="unknown",
            program_name="unknown",
            user_start_at="2026-01-01T10:00:00+00:00",
            user_complete_at="2026-01-01T11:00:00+00:00",
            observed_duration_seconds=3600,
            included_in_profile=False,
            anomaly_flags=["unlabelled_program"],
            raw={"power": []},
            derived={"quality": "unlabelled"},
            schema_version=2,
        )
    ]
    profile = build_profile_from_runs("daily_wash", runs)
    assert profile.real_run_count == 0
