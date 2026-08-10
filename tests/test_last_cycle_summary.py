"""Last cycle summary storage contract."""

from __future__ import annotations


def test_last_cycle_summary_uses_duration_seconds():
    summary = {
        "cycle_id": "test",
        "duration_seconds": 3600,
        "energy_wh": 450.0,
        "program": "daily_wash",
    }
    assert isinstance(summary["duration_seconds"], int)
    assert "duration" not in summary or summary.get("duration") != summary["completed_at"]
