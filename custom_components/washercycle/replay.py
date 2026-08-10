"""Replay harness for WasherCycle detector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .detector import CycleDetector, DetectorInput, DetectorResult
from .metrics import compute_cycle_metrics
from .models import DetectorConfig, SampleSource
from .normalizer import InputNormalizer
from .profiles import seed_profiles


@dataclass
class ReplayEvent:
    """Single replay event."""

    timestamp: datetime
    kind: str
    value: Any = None
    entity: str | None = None


@dataclass
class ReplayResult:
    """Replay output."""

    transitions: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    announcement_decisions: list[str] = field(default_factory=list)
    final_cycle: dict[str, Any] = field(default_factory=dict)
    program_rankings: list[dict[str, Any]] = field(default_factory=list)
    completion_time: str | None = None
    latency_vs_chirp: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class ReplayHarness:
    """Feed timestamped events into production detector."""

    def __init__(
        self,
        config: DetectorConfig | None = None,
        profiles: dict | None = None,
    ) -> None:
        self.config = config or DetectorConfig()
        self.profiles = profiles or {pid: p for pid, p in seed_profiles().items()}
        self.normalizer = InputNormalizer()
        self.detector = CycleDetector(
            config=self.config,
            profiles=self.profiles,
        )
        self._marked_chirp: datetime | None = None
        self._all_transitions: list[dict[str, Any]] = []
        self._all_events: list[dict[str, Any]] = []
        self._announcements: list[str] = []

    def feed(self, event: ReplayEvent) -> DetectorResult | None:
        """Feed a single event."""
        if event.kind == "restart":
            return None
        if event.kind == "user_start_recording":
            return None
        if event.kind == "user_mark_complete":
            self._marked_chirp = event.timestamp
            return None

        inp = self._event_to_input(event)
        if inp is None:
            return None

        result = self.detector.process(inp)
        self._all_transitions.extend(
            {
                "timestamp": t.timestamp,
                "from": t.from_state,
                "to": t.to_state,
                "reason": t.reason,
            }
            for t in result.transitions
        )
        for evt in result.events:
            self._all_events.append(
                {"name": evt.name, "data": evt.data, "timestamp": event.timestamp.isoformat()}
            )

        return result

    def run(self, events: list[ReplayEvent]) -> ReplayResult:
        """Run full replay."""
        for event in sorted(events, key=lambda e: e.timestamp):
            self.feed(event)

        completion_time = self.detector.cycle.completed_at
        latency = None
        if completion_time and self._marked_chirp:
            ct = datetime.fromisoformat(completion_time.replace("Z", "+00:00"))
            latency = (ct - self._marked_chirp).total_seconds()

        return ReplayResult(
            transitions=self._all_transitions,
            events=self._all_events,
            announcement_decisions=self._announcements,
            final_cycle=self.detector.cycle.to_dict(),
            completion_time=completion_time,
            latency_vs_chirp=latency,
            metrics=compute_cycle_metrics(
                cycle_id=self.detector.cycle.cycle_id,
                started_at=self.detector.cycle.started_at,
                completed_at=self.detector.cycle.completed_at,
                detected_at=self.detector.cycle.completion_detected_at,
                expected_completion_at=self.detector.cycle.expected_completion_at,
                program_id=self.detector.cycle.detected_program,
                program_confidence=self.detector.cycle.program_confidence,
                program_identified_at=self.detector.cycle.program_identified_at,
                completion_reason=self.detector.cycle.completion_reason,
                match_rejection_reason=self.detector.cycle.match_rejection_reason,
                trace=self.detector.cycle.trace_compact,
                prediction_timeline=self.detector.cycle.prediction_timeline,
            ),
        )

    def _event_to_input(self, event: ReplayEvent) -> DetectorInput | None:
        if event.kind == "power":
            power = self.normalizer.normalize_power(
                event.entity or "sensor.power", str(event.value), event.timestamp
            )
            return DetectorInput(
                timestamp=event.timestamp,
                power_w=power.watts if power else None,
                power_available=power is not None,
                source=SampleSource.POWER,
            )
        if event.kind == "energy":
            energy = self.normalizer.normalize_energy(
                event.entity or "sensor.energy", str(event.value), event.timestamp
            )
            return DetectorInput(
                timestamp=event.timestamp,
                energy_wh=energy.watt_hours if energy else None,
                energy_available=energy is not None,
                source=SampleSource.ENERGY,
            )
        if event.kind == "movement":
            mv = self.normalizer.normalize_bool(
                event.entity or "binary_sensor.moving",
                "on" if event.value else "off",
                event.timestamp,
            )
            return DetectorInput(
                timestamp=event.timestamp,
                movement=mv.value if mv else None,
                movement_available=mv is not None,
                source=SampleSource.MOVEMENT,
            )
        if event.kind == "door":
            door = self.normalizer.normalize_bool(
                event.entity or "binary_sensor.door",
                "on" if event.value else "off",
                event.timestamp,
                on_means_true=True,
            )
            return DetectorInput(
                timestamp=event.timestamp,
                door_open=door.value if door else None,
                door_available=door is not None,
                source=SampleSource.DOOR,
            )
        if event.kind == "source_unavailable":
            return DetectorInput(timestamp=event.timestamp, power_available=False)
        if event.kind == "source_restored":
            return DetectorInput(timestamp=event.timestamp, power_available=True)
        return None
