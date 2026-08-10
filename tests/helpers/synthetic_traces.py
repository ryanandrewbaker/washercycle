"""Synthetic trace factories for unit tests.

These traces are algorithm validation fixtures only. They do not represent
measurements from the Samsung WW75J54E0IW/SA washer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


def _power_events(base: datetime, profile: list[tuple[int, float]]) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": (base + timedelta(seconds=offset)).isoformat(),
            "kind": "power",
            "value": watts,
        }
        for offset, watts in profile
    ]


def synthetic_quick_wash(base: datetime | None = None) -> dict[str, Any]:
    """Short high-activity synthetic cycle (~45 min)."""
    base = base or datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    profile = [(0, 3), (30, 120), (300, 180), (600, 90), (1200, 40), (1800, 15), (2400, 3)]
    return {
        "program_id": "quick_wash",
        "synthetic": True,
        "events": _power_events(base, profile),
    }


def synthetic_daily_wash(base: datetime | None = None) -> dict[str, Any]:
    """Medium synthetic cycle (~90 min) with heater plateaus."""
    base = base or datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    profile = [
        (0, 3),
        (60, 80),
        (600, 200),
        (1200, 220),
        (1800, 150),
        (2400, 100),
        (3000, 60),
        (3600, 20),
        (4200, 8),
        (4800, 3),
    ]
    return {
        "program_id": "daily_wash",
        "synthetic": True,
        "events": _power_events(base, profile),
    }


def synthetic_bedding(base: datetime | None = None) -> dict[str, Any]:
    """Long synthetic cycle (~150 min) with extended heater periods."""
    base = base or datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    profile = [
        (0, 3),
        (120, 100),
        (900, 280),
        (1800, 300),
        (3600, 250),
        (5400, 180),
        (7200, 90),
        (8100, 25),
        (8700, 4),
    ]
    return {
        "program_id": "bedding",
        "synthetic": True,
        "events": _power_events(base, profile),
    }


def synthetic_drum_clean(base: datetime | None = None) -> dict[str, Any]:
    """Very long low-variance synthetic cycle (~120 min)."""
    base = base or datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    profile = [
        (0, 3),
        (180, 60),
        (1200, 120),
        (2400, 140),
        (3600, 130),
        (4800, 110),
        (6000, 80),
        (6600, 20),
        (6900, 3),
    ]
    return {
        "program_id": "drum_clean",
        "synthetic": True,
        "events": _power_events(base, profile),
    }


SYNTHETIC_PROGRAMS = {
    "quick_wash": synthetic_quick_wash,
    "daily_wash": synthetic_daily_wash,
    "bedding": synthetic_bedding,
    "drum_clean": synthetic_drum_clean,
}
