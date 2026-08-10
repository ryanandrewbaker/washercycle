"""Hardware preset for Samsung WW75J54E0IW/SA + SmartThings GP-WOU019BBDWG."""

from __future__ import annotations

APPLIANCE_PRESET: dict[str, float | int | bool] = {
    "start_power_w": 19.0,
    "standby_power_w": 5.0,
    "start_sustain_seconds": 30,
    "start_min_energy_wh": 1.0,
    "standby_confirm_seconds": 60,
    "provisional_min_duration_seconds": 900,
    "post_completion_seconds": 30,
    "resample_interval_seconds": 15,
    "matcher_confidence_threshold": 0.70,
    "matcher_margin": 0.12,
    "matcher_hysteresis_score": 0.55,
    "min_real_runs_recognition": 3,
    "max_reporting_gap_p95_seconds": 120.0,
    "rewash_delay_minutes": 120,
    "tick_interval_fast_seconds": 10,
    "tick_interval_slow_seconds": 30,
}
