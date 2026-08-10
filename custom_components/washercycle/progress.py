"""Progress and ETA calculation for WasherCycle."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import EtaConfidence, ProgramMatchState, ProgramProfile
from .resample import parse_ts


def compute_progress(
    *,
    started_at: str | None,
    now: datetime,
    profile: ProgramProfile | None,
    program_match_state: ProgramMatchState,
    current_progress: float = 0.0,
    internal_state: str = "RUNNING",
    immediately_emptied: bool = False,
) -> tuple[float, int | None, datetime | None, str]:
    """Compute progress, remaining seconds, expected completion, ETA confidence."""
    if not started_at:
        return 0.0, None, None, EtaConfidence.UNKNOWN

    start = parse_ts(started_at)
    elapsed = (now - start).total_seconds()

    if internal_state in ("NEEDS_EMPTYING", "NEEDS_REWASH") and not immediately_emptied:
        return 100.0, 0, None, EtaConfidence.MATCHED

    if internal_state == "IDLE" and immediately_emptied:
        return 100.0, 0, None, EtaConfidence.MATCHED

    if program_match_state in (ProgramMatchState.UNKNOWN, ProgramMatchState.DETECTING):
        if profile and profile.duration_median_seconds > 0:
            provisional_total = profile.duration_median_seconds
            progress = min(99.0, (elapsed / provisional_total) * 100)
            expected = start + timedelta(seconds=provisional_total)
            remaining = max(0, int(provisional_total - elapsed))
            return max(current_progress, progress), remaining, expected, EtaConfidence.PROVISIONAL
        return max(current_progress, min(50.0, elapsed / 3600 * 100)), None, None, EtaConfidence.UNKNOWN

    if not profile or profile.duration_median_seconds <= 0:
        return current_progress, None, None, EtaConfidence.UNAVAILABLE

    expected = start + timedelta(seconds=profile.duration_median_seconds)
    remaining = max(0, int((expected - now).total_seconds()))
    total = profile.duration_median_seconds
    progress = min(99.0, (elapsed / total) * 100) if total > 0 else 0.0

    eta_conf = EtaConfidence.MATCHED
    mad = profile.duration_mad_seconds or profile.duration_median_seconds * 0.1
    if elapsed > profile.duration_median_seconds + 2 * mad:
        eta_conf = EtaConfidence.EXTENDED
        remaining = None
        expected = None

    return max(current_progress, progress), remaining, expected, eta_conf
