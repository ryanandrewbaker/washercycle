"""Automatic cycle archiving with deferred post-completion finalisation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from .const import PROGRAM_CATALOGUE
from .models import CycleRecord, TrainingRun
from .resample import parse_ts


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CycleArchive:
    """Build and persist training runs from completed cycles."""

    def __init__(self, post_completion_seconds: int = 30) -> None:
        self.post_completion_seconds = post_completion_seconds
        self._pending: dict[str, CycleRecord] = {}

    def begin_post_window(self, cycle: CycleRecord) -> None:
        """Schedule post-completion recording for a completed cycle."""
        now = datetime.now(timezone.utc)
        cycle.archive_pending = True
        cycle.post_window_until = (
            now + timedelta(seconds=self.post_completion_seconds)
        ).isoformat()
        self._pending[cycle.cycle_id] = cycle

    def is_pending(self, cycle_id: str) -> bool:
        return cycle_id in self._pending

    def get_pending(self, cycle_id: str) -> CycleRecord | None:
        return self._pending.get(cycle_id)

    def should_finalize(self, cycle: CycleRecord, now: datetime) -> bool:
        if not cycle.archive_pending or not cycle.post_window_until:
            return False
        return now >= parse_ts(cycle.post_window_until)

    def finalize(
        self,
        cycle: CycleRecord,
        *,
        resample_interval: int = 15,
    ) -> TrainingRun:
        """Build training run from cycle trace and clear pending state."""
        self._pending.pop(cycle.cycle_id, None)
        cycle.archive_pending = False
        cycle.post_window_until = None

        program_id = cycle.calibration_program_id or cycle.detected_program or "daily_wash"
        if program_id == "auto":
            program_id = cycle.detected_program or "daily_wash"
        program_name = PROGRAM_CATALOGUE.get(program_id, program_id)

        start_at = cycle.started_at or _iso_now()
        complete_at = cycle.completed_at or _iso_now()
        duration = (parse_ts(complete_at) - parse_ts(start_at)).total_seconds()

        power_raw = [
            {"t": p["timestamp"], "w": p.get("power_w", 0)}
            for p in cycle.trace_compact
            if p.get("power_w") is not None
        ]
        energy_raw = [
            {"t": p["timestamp"], "w": p.get("energy_wh", 0)}
            for p in cycle.trace_compact
            if p.get("energy_wh") is not None
        ]

        peak = max((s["w"] for s in power_raw), default=0.0)
        mean = (
            sum(s["w"] for s in power_raw) / len(power_raw) if power_raw else 0.0
        )

        quality = "auto"
        if cycle.calibration_program_id and cycle.calibration_program_id != "auto":
            quality = "calibration_label"

        derived: dict[str, Any] = {
            "auto_detected_start_at": start_at,
            "auto_detected_complete_at": complete_at,
            "cycle_energy_wh": cycle.accumulated_energy_wh,
            "peak_power_w": peak,
            "mean_power_w": mean,
            "completion_latency_seconds": cycle.completion_detection_latency_seconds,
            "quality": quality,
            "trace_sample_count": len(power_raw),
        }

        run = TrainingRun(
            run_id=str(uuid.uuid4()),
            program_id=program_id,
            program_name=program_name,
            user_start_at=start_at,
            user_complete_at=complete_at,
            observed_duration_seconds=duration,
            included_in_profile=quality in ("auto", "calibration_label"),
            confirmed=True,
            note="",
            anomaly_flags=[] if quality != "manual_timing" else ["manual_timing"],
            raw={"power": power_raw, "energy": energy_raw},
            derived=derived,
            schema_version=2,
        )
        return run

    def restore_pending(self, cycle: CycleRecord) -> None:
        if cycle.archive_pending:
            self._pending[cycle.cycle_id] = cycle
