"""Training recording for WasherCycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .const import PROGRAM_CATALOGUE
from .models import ActiveRecording, TrainingRun
from .resample import parse_ts, resample_trace
from .stats import median


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


class TrainingRecorder:
    """Manage training recording lifecycle."""

    def __init__(self, recording: ActiveRecording | None = None) -> None:
        self._recording = recording or ActiveRecording()

    @property
    def recording(self) -> ActiveRecording:
        return self._recording

    @property
    def is_active(self) -> bool:
        return self._recording.active

    def start(self, program_id: str) -> str:
        """Start a new training recording."""
        if self._recording.active:
            raise ValueError("Recording already active")
        run_id = str(uuid.uuid4())
        self._recording = ActiveRecording(
            active=True,
            run_id=run_id,
            program_id=program_id,
            started_at=_iso_now(),
            samples=[],
        )
        return run_id

    def cancel(self) -> None:
        """Cancel active recording."""
        self._recording = ActiveRecording()

    def add_sample(self, sample: dict[str, Any]) -> None:
        """Add a timestamped sample to active recording."""
        if not self._recording.active:
            return
        self._recording.samples.append(sample)
        if len(self._recording.samples) > 20000:
            self._recording.samples = self._recording.samples[-20000:]

    def mark_complete_and_save(
        self,
        *,
        auto_detected_start_at: str | None = None,
        auto_detected_complete_at: str | None = None,
        resample_interval: int = 15,
    ) -> TrainingRun:
        """Mark complete and build training run."""
        if not self._recording.active or not self._recording.run_id:
            raise ValueError("No active recording")

        complete_at = _iso_now()
        start_at = self._recording.started_at or complete_at
        program_id = self._recording.program_id or "daily_wash"
        program_name = PROGRAM_CATALOGUE.get(program_id, program_id)

        duration = (_parse_ts(complete_at) - _parse_ts(start_at)).total_seconds()

        raw = self._organize_raw_samples(self._recording.samples)
        derived = self._compute_derived(
            raw,
            start_at,
            complete_at,
            auto_detected_start_at,
            auto_detected_complete_at,
            resample_interval,
        )

        run = TrainingRun(
            run_id=self._recording.run_id,
            program_id=program_id,
            program_name=program_name,
            user_start_at=start_at,
            user_complete_at=complete_at,
            observed_duration_seconds=duration,
            included_in_profile=True,
            confirmed=True,
            raw=raw,
            derived=derived,
        )

        self._recording = ActiveRecording()
        return run

    def _organize_raw_samples(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        """Organize flat samples into raw trace structure."""
        raw: dict[str, list] = {
            "power": [],
            "energy": [],
            "movement": [],
            "door": [],
            "plug_switch": [],
            "unavailable": [],
            "linkquality": [],
        }
        for s in samples:
            kind = s.get("kind")
            ts = s.get("timestamp", _iso_now())
            if kind == "power":
                raw["power"].append({"t": ts, "w": s.get("value"), "q": s.get("quality", "ok")})
            elif kind == "energy":
                raw["energy"].append({"t": ts, "wh": s.get("value"), "q": s.get("quality", "ok")})
            elif kind == "movement":
                raw["movement"].append({"t": ts, "v": s.get("value")})
            elif kind == "door":
                raw["door"].append({"t": ts, "open": s.get("value")})
            elif kind == "plug_switch":
                raw["plug_switch"].append({"t": ts, "on": s.get("value")})
            elif kind == "unavailable":
                raw["unavailable"].append(s)
            elif kind == "linkquality":
                raw["linkquality"].append(s)
        return raw

    def _compute_derived(
        self,
        raw: dict[str, Any],
        start_at: str,
        complete_at: str,
        auto_start: str | None,
        auto_complete: str | None,
        resample_interval: int,
    ) -> dict[str, Any]:
        """Compute derived metrics from raw trace."""
        power = raw.get("power", [])
        energy = raw.get("energy", [])

        power_vals = [p["w"] for p in power if p.get("w") is not None]
        peak = max(power_vals) if power_vals else 0.0
        mean_p = sum(power_vals) / len(power_vals) if power_vals else 0.0

        cycle_energy = 0.0
        if len(energy) >= 2:
            start_wh = energy[0].get("wh", 0) or 0
            end_wh = energy[-1].get("wh", 0) or 0
            cycle_energy = max(0.0, end_wh - start_wh)

        standby_vals = [p["w"] for p in power[-20:] if p.get("w") is not None]
        standby = median(standby_vals) if standby_vals else 0.0

        resampled = []
        if power:
            origin = parse_ts(power[0]["t"])
            resampled = resample_trace(power, origin=origin, interval_s=resample_interval)

        latency = None
        if auto_complete:
            latency = (_parse_ts(auto_complete) - _parse_ts(complete_at)).total_seconds()

        return {
            "cleaned_power": power,
            "resampled_power": resampled,
            "cycle_energy_wh": cycle_energy,
            "peak_power_w": peak,
            "mean_power_w": mean_p,
            "standby_power_w": standby,
            "movement_active_periods": [],
            "power_transitions": [],
            "low_power_periods": [],
            "final_signature_window": [],
            "auto_detected_start_at": auto_start,
            "auto_detected_complete_at": auto_complete,
            "completion_latency_seconds": latency,
        }

    def restore(self, recording: ActiveRecording) -> None:
        """Restore active recording from storage."""
        self._recording = recording
