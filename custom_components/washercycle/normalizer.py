"""Input normalisation layer for WasherCycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import (
    NormalizedBool,
    NormalizedEnergy,
    NormalizedPower,
    RejectedSample,
    SampleQuality,
)


@dataclass
class NormalizerState:
    """Stateful normalizer tracking last readings."""

    last_power: NormalizedPower | None = None
    last_energy: NormalizedEnergy | None = None
    last_movement: NormalizedBool | None = None
    last_door: NormalizedBool | None = None
    last_plug_on: NormalizedBool | None = None
    rejected: list[RejectedSample] = field(default_factory=list)
    energy_baseline_wh: float | None = None
    max_stale_seconds: float = 120.0
    impossible_spike_w: float = 3000.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize last known values."""
        return {
            "energy_baseline_wh": self.energy_baseline_wh,
            "last_power_w": self.last_power.watts if self.last_power else None,
            "last_energy_wh": self.last_energy.watt_hours if self.last_energy else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NormalizerState:
        """Restore normalizer state."""
        state = cls()
        state.energy_baseline_wh = data.get("energy_baseline_wh")
        return state


def _parse_timestamp(ts: datetime | str) -> datetime:
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _is_missing(value: str | None) -> bool:
    return value is None or value in ("unknown", "unavailable", "")


class InputNormalizer:
    """Normalise Home Assistant entity values into domain samples."""

    def __init__(self, state: NormalizerState | None = None) -> None:
        self._state = state or NormalizerState()

    @property
    def state(self) -> NormalizerState:
        return self._state

    def normalize_power(
        self,
        entity_id: str,
        raw_value: str | None,
        timestamp: datetime | str,
    ) -> NormalizedPower | None:
        """Parse and validate a power reading."""
        ts = _parse_timestamp(timestamp)
        if _is_missing(raw_value):
            self._reject(entity_id, ts, str(raw_value), "missing")
            return None
        try:
            watts = float(raw_value)
        except (TypeError, ValueError):
            self._reject(entity_id, ts, str(raw_value), "unparseable")
            return None
        if watts < 0:
            self._reject(entity_id, ts, str(raw_value), "negative_power")
            return None

        quality = SampleQuality.OK
        last = self._state.last_power
        if last is not None:
            delta_w = abs(watts - last.watts)
            delta_t = (ts - last.timestamp).total_seconds()
            if delta_w == 0 and delta_t >= self._state.max_stale_seconds:
                quality = SampleQuality.STALE
            elif delta_t > 0 and delta_w > self._state.impossible_spike_w:
                quality = SampleQuality.SPIKE
                self._reject(entity_id, ts, str(raw_value), "impossible_spike")
                return None
            elif delta_w == 0 and delta_t < 1:
                return None

        sample = NormalizedPower(timestamp=ts, watts=watts, quality=quality)
        self._state.last_power = sample
        return sample

    def normalize_energy(
        self,
        entity_id: str,
        raw_value: str | None,
        timestamp: datetime | str,
        *,
        energy_in_kwh: bool = True,
    ) -> NormalizedEnergy | None:
        """Parse cumulative energy; source reports kWh, store as Wh."""
        ts = _parse_timestamp(timestamp)
        if _is_missing(raw_value):
            self._reject(entity_id, ts, str(raw_value), "missing")
            return None
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            self._reject(entity_id, ts, str(raw_value), "unparseable")
            return None

        wh = value * 1000.0 if energy_in_kwh else value
        reset_detected = False
        last = self._state.last_energy
        if last is not None and wh < last.watt_hours - 0.01:
            reset_detected = True
            self._state.energy_baseline_wh = wh

        if last is not None:
            delta_t = (ts - last.timestamp).total_seconds()
            if wh == last.watt_hours and delta_t < 1:
                return None

        sample = NormalizedEnergy(
            timestamp=ts,
            watt_hours=wh,
            quality=SampleQuality.OK,
            reset_detected=reset_detected,
        )
        self._state.last_energy = sample
        return sample

    def normalize_bool(
        self,
        entity_id: str,
        raw_value: str | None,
        timestamp: datetime | str,
        *,
        on_means_true: bool = True,
    ) -> NormalizedBool | None:
        """Parse boolean sensor (on/off)."""
        ts = _parse_timestamp(timestamp)
        if _is_missing(raw_value):
            self._reject(entity_id, ts, str(raw_value), "missing")
            return None
        is_on = raw_value == "on"
        value = is_on if on_means_true else not is_on

        last_attr = {
            "binary_sensor.laundry_washerdoor_contact": "last_door",
            "binary_sensor.laundry_washerdoor_moving": "last_movement",
        }.get(entity_id, "last_plug_on")

        last = getattr(self._state, last_attr, None)
        if last is not None and last.value == value:
            delta_t = (ts - last.timestamp).total_seconds()
            if delta_t < 1:
                return None

        sample = NormalizedBool(timestamp=ts, value=value, quality=SampleQuality.OK)
        if entity_id.endswith("contact"):
            self._state.last_door = sample
        elif entity_id.endswith("moving"):
            self._state.last_movement = sample
        else:
            self._state.last_plug_on = sample
        return sample

    def cycle_energy_wh(self, current_wh: float | None) -> float:
        """Calculate cycle energy since baseline."""
        if current_wh is None:
            return 0.0
        baseline = self._state.energy_baseline_wh
        if baseline is None:
            return 0.0
        return max(0.0, current_wh - baseline)

    def set_energy_baseline(self, wh: float | None) -> None:
        """Set energy baseline at cycle start."""
        self._state.energy_baseline_wh = wh

    def _reject(self, entity: str, ts: datetime, raw: str, reason: str) -> None:
        self._state.rejected.append(
            RejectedSample(entity=entity, timestamp=ts, raw_value=raw, reason=reason)
        )
        if len(self._state.rejected) > 200:
            self._state.rejected = self._state.rejected[-200:]

    def is_stale(self, timestamp: datetime, now: datetime) -> bool:
        """Check if a timestamp is stale."""
        return (now - timestamp).total_seconds() > self._state.max_stale_seconds
