"""Representative WasherCycle v1 storage payloads for migration tests."""

from __future__ import annotations

from typing import Any


def sample_v1_storage_payload(entry_id: str) -> dict[str, Any]:
    """Build a representative v1 WasherCycle storage payload."""
    return {
        "version": 1,
        "config_entry_id": entry_id,
        "pending_program": "quick_wash",
        "announcement_state": {
            "completion_cycle-live": "2026-08-10T08:00:00+00:00",
            "rewash_cycle-live": "2026-08-10T10:00:00+00:00",
        },
        "current_cycle": {
            "cycle_id": "cycle-live",
            "internal_state": "running",
            "public_state": "running",
            "started_at": "2026-08-10T07:00:00+00:00",
            "selected_program": "auto",
            "detected_program": "daily_wash",
            "program_confidence": 0.82,
            "trace_compact": [
                {
                    "timestamp": "2026-08-10T07:05:00+00:00",
                    "power_w": 145.0,
                }
            ],
        },
        "training_runs": [
            {
                "run_id": "run-calibration-1",
                "program_id": "daily_wash",
                "program_name": "Daily Wash",
                "user_start_at": "2026-08-09T07:00:00+00:00",
                "user_complete_at": "2026-08-09T08:30:00+00:00",
                "observed_duration_seconds": 5400.0,
                "included_in_profile": True,
                "confirmed": True,
                "note": "manual timing calibration",
                "raw": {"power": [{"t": "2026-08-09T07:00:00+00:00", "w": 120.0}]},
                "derived": {"peak_power_w": 180.0},
            }
        ],
        "profiles": {
            "daily_wash": {
                "program_id": "daily_wash",
                "display_name": "Daily Wash",
                "accepted_run_ids": ["run-calibration-1"],
                "duration_median_seconds": 5400.0,
                "duration_mad_seconds": 120.0,
                "profile_schema_version": 1,
            }
        },
        "active_recording": {
            "active": False,
            "run_id": None,
            "program_id": None,
            "started_at": None,
            "samples": [],
        },
        "completed_history": [
            {
                "cycle_id": "cycle-old",
                "duration_seconds": 5100,
                "program": "daily_wash",
            }
        ],
        "latency_stats": {
            "samples": [],
            "median_seconds": None,
            "mad_seconds": None,
        },
        "normalizer_state": {"last_energy_wh": 12.5},
        "recent_transitions": [],
        "data_quality_counters": {"power_gap": 1},
        "raw_run_retention": 50,
        "completed_history_retention": 20,
    }
