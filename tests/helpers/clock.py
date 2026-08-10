"""Injectable clock for algorithm tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


class FakeClock:
    """Controllable UTC clock for deterministic tests."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 7, 31, 10, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> datetime:
        self._now = self._now + timedelta(seconds=seconds)
        return self._now

    def set(self, when: datetime) -> None:
        self._now = when
