"""Tests for replay harness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.washercycle.replay import ReplayEvent, ReplayHarness


def test_replay_start_and_complete():
    base = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    events = []
    for i in range(20):
        events.append(
            ReplayEvent(
                timestamp=base + timedelta(seconds=i * 10),
                kind="power",
                value=50.0 if i < 15 else 2.0,
            )
        )
    events.append(ReplayEvent(timestamp=base + timedelta(seconds=200), kind="door", value=True))

    harness = ReplayHarness()
    result = harness.run(events)
    assert len(result.transitions) > 0
