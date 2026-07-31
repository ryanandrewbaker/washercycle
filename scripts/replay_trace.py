#!/usr/bin/env python3
"""Replay a WasherCycle trace file."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.washercycle.replay import ReplayEvent, ReplayHarness


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay WasherCycle trace")
    parser.add_argument("trace_file", help="JSON trace file")
    args = parser.parse_args()

    with open(args.trace_file) as f:
        data = json.load(f)

    events = []
    for item in data.get("events", data):
        events.append(
            ReplayEvent(
                timestamp=datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")),
                kind=item["kind"],
                value=item.get("value"),
                entity=item.get("entity"),
            )
        )

    harness = ReplayHarness()
    result = harness.run(events)

    print(json.dumps(
        {
            "transitions": result.transitions,
            "events": result.events,
            "announcements": result.announcement_decisions,
            "completion_time": result.completion_time,
            "latency_vs_chirp": result.latency_vs_chirp,
            "final_state": result.final_cycle.get("public_state"),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
