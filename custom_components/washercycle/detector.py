"""Cycle detector state machine for WasherCycle."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .completion import assess_completion
from .const import (
    EVENT_CYCLE_COMPLETED,
    EVENT_CYCLE_EMPTIED,
    EVENT_NEEDS_REWASH,
    EVENT_PROGRAM_IDENTIFIED,
)
from .matcher import match_program
from .models import (
    INTERNAL_TO_PUBLIC,
    CycleRecord,
    DetectorConfig,
    DoorCorrelationClass,
    InternalState,
    ProgramMatchState,
    PublicState,
    SampleSource,
    StateTransition,
)
from .preset import APPLIANCE_PRESET
from .progress import compute_progress


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@dataclass
class DetectorEvent:
    """Event emitted by detector."""

    name: str
    data: dict[str, Any] = field(default_factory=dict)
    shadow: bool = False


@dataclass
class DetectorResult:
    """Result of processing an input."""

    cycle: CycleRecord
    events: list[DetectorEvent] = field(default_factory=list)
    transitions: list[StateTransition] = field(default_factory=list)
    finalize_archive: bool = False


@dataclass
class DetectorInput:
    """Normalised input to detector."""

    timestamp: datetime
    power_w: float | None = None
    energy_wh: float | None = None
    door_open: bool | None = None
    movement: bool | None = None
    plug_on: bool | None = None
    power_available: bool = True
    energy_available: bool = True
    door_available: bool = True
    movement_available: bool = True
    source: SampleSource = SampleSource.OTHER


class CycleDetector:
    """Pure Python cycle state machine."""

    def __init__(
        self,
        config: DetectorConfig,
        cycle: CycleRecord | None = None,
        profiles: dict | None = None,
        pending_program: str = "auto",
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.cycle = cycle or CycleRecord(cycle_id=str(uuid.uuid4()))
        self.profiles = profiles or {}
        self.pending_program = pending_program
        self.transitions: list[StateTransition] = []
        self._energy_at_last_check: float | None = None
        self._energy_stable_since: datetime | None = None
        self._last_power_sample: tuple[str, float] | None = None
        self._now_fn = now_fn or (lambda: datetime.now(UTC))

    def restore(self, cycle: CycleRecord, pending_program: str = "auto") -> None:
        """Restore detector from persisted cycle."""
        self.cycle = cycle
        self.cycle.restart_recovered = True
        self.pending_program = pending_program

    def process(self, inp: DetectorInput) -> DetectorResult:
        """Process one normalised input from a source entity."""
        events: list[DetectorEvent] = []
        now = inp.timestamp

        self._update_availability(inp)
        self._update_energy_accumulation(inp)

        state = InternalState(self.cycle.internal_state)

        if state == InternalState.IDLE:
            events = self._handle_idle(inp, events)
        elif state == InternalState.START_CANDIDATE:
            events = self._handle_start_candidate(inp, events)
        elif state in (InternalState.RUNNING, InternalState.PAUSED):
            events = self._handle_running(inp, events)
        elif state == InternalState.NEEDS_EMPTYING:
            events = self._handle_needs_emptying(inp, events)
        elif state == InternalState.NEEDS_REWASH:
            events = self._handle_needs_rewash(inp, events)

        state = InternalState(self.cycle.internal_state)
        if self.cycle.door_open_pending_at and state not in (
            InternalState.IDLE,
            InternalState.NEEDS_EMPTYING,
            InternalState.NEEDS_REWASH,
        ):
            events = self._handle_door_correlation(inp, events)

        if (
            state
            in (
                InternalState.RUNNING,
                InternalState.PAUSED,
                InternalState.NEEDS_EMPTYING,
            )
            or self.cycle.archive_pending
        ):
            events = self._handle_door_emptying(inp, events)

        if (
            self._should_record_trace()
            and inp.source == SampleSource.POWER
            and inp.power_w is not None
        ):
            self._append_power_trace(inp)

        self._update_matching(now, events)
        return DetectorResult(
            cycle=self.cycle,
            events=events,
            transitions=self.transitions[-10:],
            finalize_archive=False,
        )

    def tick(self, now: datetime, *, energy_wh: float | None = None) -> DetectorResult:
        """Advance timers only — does not append trace samples."""
        events: list[DetectorEvent] = []
        finalize = False
        state = InternalState(self.cycle.internal_state)

        if state == InternalState.START_CANDIDATE and self.cycle.start_candidate_at:
            candidate_start = _parse_ts(self.cycle.start_candidate_at)
            elapsed = (now - candidate_start).total_seconds()
            if elapsed >= self.config.start_sustain_seconds:
                self.cycle.started_at = self.cycle.start_candidate_at
                self._ensure_energy_baseline(energy_wh)
                self._consume_calibration_label()
                evt = self._transition(
                    InternalState.RUNNING,
                    "cycle_confirmed_start_tick",
                    now,
                    event="washercycle_cycle_started",
                    event_data=self._cycle_event_data(),
                )
                if evt:
                    events.append(evt)

        if state in (InternalState.RUNNING, InternalState.PAUSED):
            events = self._check_completion(now, events, power_w=None)

        if state == InternalState.NEEDS_EMPTYING:
            events = self._handle_needs_emptying_tick(now, events)

        if self.cycle.archive_pending and self.cycle.post_window_until:  # noqa: SIM102
            if now >= _parse_ts(self.cycle.post_window_until):
                finalize = True

        self._update_matching(now, events)
        return DetectorResult(
            cycle=self.cycle,
            events=events,
            transitions=self.transitions[-10:],
            finalize_archive=finalize,
        )

    def _consume_calibration_label(self) -> None:
        if self.pending_program != "auto" and not self.cycle.calibration_label_consumed:
            self.cycle.calibration_program_id = self.pending_program
            self.cycle.calibration_label_consumed = True
            self.cycle.selected_program = self.pending_program
            self.cycle.detected_program = self.pending_program
            self.cycle.program_source = "calibration"
            self.cycle.program_match_state = ProgramMatchState.MANUAL

    def _transition(
        self,
        to_state: InternalState,
        reason: str,
        now: datetime,
        *,
        event: str | None = None,
        event_data: dict | None = None,
    ) -> DetectorEvent | None:
        from_state = InternalState(self.cycle.internal_state)
        if from_state == to_state:
            return None
        self.cycle.internal_state = to_state
        self.cycle.public_state = INTERNAL_TO_PUBLIC.get(to_state, PublicState.UNAVAILABLE)
        self.cycle.state_reason = reason
        self.cycle.last_transition_at = now.isoformat()
        self.transitions.append(
            StateTransition(
                timestamp=now.isoformat(),
                from_state=from_state.value,
                to_state=to_state.value,
                reason=reason,
                event=event,
            )
        )
        if event and not self.cycle.events_emitted.get(event):
            self.cycle.events_emitted[event] = True
            shadow = self.config.shadow_mode
            return DetectorEvent(
                name=event,
                data=event_data or {},
                shadow=shadow,
            )
        return None

    def _handle_idle(self, inp: DetectorInput, events: list) -> list:
        if inp.power_w is None or not inp.power_available:
            return events
        if inp.power_w < self.config.start_power_w:
            return events
        if inp.door_open is True:
            return events

        now = inp.timestamp
        self._begin_new_cycle(now, energy_at_start_wh=inp.energy_wh)
        evt = self._transition(InternalState.START_CANDIDATE, "power_above_threshold", now)
        if evt:
            events.append(evt)
        return events

    def _handle_start_candidate(self, inp: DetectorInput, events: list) -> list:
        now = inp.timestamp
        if not self.cycle.start_candidate_at:
            return events

        candidate_start = _parse_ts(self.cycle.start_candidate_at)
        elapsed = (now - candidate_start).total_seconds()

        if inp.door_open is True or (  # noqa: SIM102
            inp.power_w is not None and inp.power_w < self.config.start_power_w
        ):
            if elapsed < self.config.start_sustain_seconds:
                evt = self._transition(InternalState.IDLE, "start_candidate_cancelled", now)
                self.cycle.start_candidate_at = None
                if evt:
                    events.append(evt)
                return events

        if inp.power_w is not None and inp.power_w >= self.config.start_power_w:  # noqa: SIM102
            if elapsed >= self.config.start_sustain_seconds:
                self.cycle.started_at = self.cycle.start_candidate_at
                self._ensure_energy_baseline(inp.energy_wh)
                self._consume_calibration_label()
                evt = self._transition(
                    InternalState.RUNNING,
                    "cycle_confirmed_start",
                    now,
                    event="washercycle_cycle_started",
                    event_data=self._cycle_event_data(),
                )
                if evt:
                    events.append(evt)
        return events

    def _handle_running(self, inp: DetectorInput, events: list) -> list:
        now = inp.timestamp
        state = InternalState(self.cycle.internal_state)

        if inp.power_w is not None and inp.power_w < self.config.standby_power_w:
            if not self.cycle.standby_since:
                self.cycle.standby_since = now.isoformat()
        else:
            self.cycle.standby_since = None

        if (
            inp.power_w is not None
            and inp.power_w < self.config.standby_power_w
            and inp.movement is False
            and state == InternalState.RUNNING
        ):
            self.cycle.paused_at = now.isoformat()
            evt = self._transition(InternalState.PAUSED, "low_power_pause", now)
            if evt:
                events.append(evt)
        elif (
            inp.power_w is not None
            and inp.power_w >= self.config.standby_power_w
            and state == InternalState.PAUSED
        ):
            self.cycle.paused_at = None
            evt = self._transition(InternalState.RUNNING, "activity_resumed", now)
            if evt:
                events.append(evt)

        if inp.door_open is True and not self.cycle.door_open_pending_at:
            self.cycle.door_open_pending_at = now.isoformat()
            self.cycle.door_correlation_class = DoorCorrelationClass.PENDING.value

        return self._check_completion(now, events, power_w=inp.power_w)

    def _check_completion(self, now: datetime, events: list, *, power_w: float | None) -> list:
        if not self.cycle.started_at:
            return events

        elapsed = (now - _parse_ts(self.cycle.started_at)).total_seconds()
        profile = None
        if self.cycle.detected_program:
            profile = self.profiles.get(self.cycle.detected_program)

        assessment = assess_completion(
            now=now,
            started_at=self.cycle.started_at,
            standby_since=self.cycle.standby_since,
            current_power_w=power_w,
            elapsed_seconds=elapsed,
            energy_wh=self.cycle.accumulated_energy_wh,
            trace=self.cycle.trace_compact,
            profile=profile,
            config=self.config,
            standby_confirm_seconds=self.config.standby_confirm_seconds,
        )

        if assessment.confirmed:
            return self._complete_cycle(
                now,
                assessment.reason,
                events,
                backdated=assessment.backdated_completed_at,
            )
        return events

    def _complete_cycle(
        self,
        now: datetime,
        reason: str,
        events: list,
        *,
        backdated: datetime | None = None,
    ) -> list:
        backdated_at = backdated or now
        self.cycle.completed_at = backdated_at.isoformat()
        self.cycle.completion_detected_at = now.isoformat()
        self.cycle.completion_reason = reason
        self.cycle.completion_detection_latency_seconds = (now - backdated_at).total_seconds()

        evt_data = self._cycle_event_data(completion_reason=reason)
        if not self.cycle.events_emitted.get(EVENT_CYCLE_COMPLETED):
            self.cycle.events_emitted[EVENT_CYCLE_COMPLETED] = True
            events.append(
                DetectorEvent(
                    name=EVENT_CYCLE_COMPLETED,
                    data=evt_data,
                    shadow=self.config.shadow_mode,
                )
            )

        self.cycle.archive_pending = True
        post_seconds = int(APPLIANCE_PRESET["post_completion_seconds"])
        self.cycle.post_window_until = (now + timedelta(seconds=post_seconds)).isoformat()
        self.cycle.progress = 100.0

        self.cycle.needs_emptying_at = now.isoformat()
        rewash_due = now + timedelta(minutes=self.config.rewash_delay_minutes)
        self.cycle.rewash_due_at = rewash_due.isoformat()
        self._transition(InternalState.NEEDS_EMPTYING, reason, now)
        return events

    def _handle_needs_emptying(self, inp: DetectorInput, events: list) -> list:
        return self._handle_needs_emptying_tick(inp.timestamp, events)

    def _handle_needs_emptying_tick(self, now: datetime, events: list) -> list:
        if self.cycle.rewash_due_at and now >= _parse_ts(self.cycle.rewash_due_at):
            evt = self._transition(
                InternalState.NEEDS_REWASH,
                "rewash_delay_expired",
                now,
                event=EVENT_NEEDS_REWASH,
                event_data=self._cycle_event_data(),
            )
            if evt:
                events.append(evt)
        return events

    def _handle_needs_rewash(self, inp: DetectorInput, events: list) -> list:
        return events

    def _handle_door_emptying(self, inp: DetectorInput, events: list) -> list:
        if inp.door_open is not True:
            return events
        state = InternalState(self.cycle.internal_state)
        if (
            state
            not in (
                InternalState.NEEDS_EMPTYING,
                InternalState.NEEDS_REWASH,
            )
            and not self.cycle.archive_pending
        ):
            return events
        return self._empty_cycle(inp.timestamp, events)

    def _handle_door_correlation(self, inp: DetectorInput, events: list) -> list:
        now = inp.timestamp
        if not self.cycle.door_open_pending_at:
            return events

        door_open = _parse_ts(self.cycle.door_open_pending_at)
        window = self.config.door_correlation_seconds
        if (now - door_open).total_seconds() > window:
            self.cycle.door_correlation_class = DoorCorrelationClass.MID_CYCLE.value
            self.cycle.door_open_pending_at = None
            return events

        if inp.power_w is not None and inp.power_w < self.config.standby_power_w:  # noqa: SIM102
            if self.cycle.standby_since:
                standby_elapsed = (now - _parse_ts(self.cycle.standby_since)).total_seconds()
                if standby_elapsed >= self.config.standby_confirm_seconds:
                    self.cycle.door_correlation_class = DoorCorrelationClass.IMMEDIATE_EMPTY.value
                    return self._complete_cycle(
                        now,
                        "door_correlated_completion",
                        events,
                        backdated=_parse_ts(self.cycle.standby_since),
                    )

        return events

    def _empty_cycle(self, now: datetime, events: list) -> list:
        self.cycle.door_correlation_class = DoorCorrelationClass.ORDINARY_UNLOAD.value
        if not self.cycle.events_emitted.get(EVENT_CYCLE_EMPTIED):
            self.cycle.events_emitted[EVENT_CYCLE_EMPTIED] = True
            events.append(
                DetectorEvent(
                    name=EVENT_CYCLE_EMPTIED,
                    data=self._cycle_event_data(),
                    shadow=self.config.shadow_mode,
                )
            )
        self.cycle.rewash_due_at = None
        self._transition(InternalState.IDLE, "door_opened_emptied", now)
        return events

    def force_empty(self, now: datetime | None = None) -> DetectorResult:
        """Diagnostic-only: manually force cycle to empty/idle."""
        now = now or self._now_fn()
        events = []
        if not self.cycle.events_emitted.get(EVENT_CYCLE_EMPTIED):
            self.cycle.events_emitted[EVENT_CYCLE_EMPTIED] = True
            events.append(
                DetectorEvent(
                    name=EVENT_CYCLE_EMPTIED,
                    data=self._cycle_event_data(),
                    shadow=True,
                )
            )
        self._transition(InternalState.IDLE, "manual_force_empty", now)
        return DetectorResult(cycle=self.cycle, events=events)

    def _update_matching(self, now: datetime, events: list) -> None:
        state = InternalState(self.cycle.internal_state)
        if state not in (
            InternalState.RUNNING,
            InternalState.PAUSED,
            InternalState.NEEDS_EMPTYING,
        ):
            return
        if not self.cycle.started_at:
            return

        elapsed = (now - _parse_ts(self.cycle.started_at)).total_seconds()
        manual = None
        if self.cycle.program_source in ("manual", "calibration"):
            manual = self.cycle.detected_program or self.cycle.calibration_program_id

        result = match_program(
            started_at=self.cycle.started_at,
            now=now,
            elapsed_seconds=elapsed,
            energy_wh=self.cycle.accumulated_energy_wh,
            trace=self.cycle.trace_compact,
            profiles=self.profiles,
            config=self.config,
            manual_program=manual,
            current_match=self.cycle.detected_program,
            current_state=ProgramMatchState(self.cycle.program_match_state),
            program_identified_emitted=self.cycle.events_emitted.get(
                EVENT_PROGRAM_IDENTIFIED, False
            ),
        )

        if result.program_id:
            self.cycle.detected_program = result.program_id
        self.cycle.program_confidence = result.confidence
        self.cycle.program_match_state = result.match_state
        self.cycle.match_rejection_reason = result.rejection_reason

        self.cycle.prediction_timeline.append(
            {
                "elapsed_s": elapsed,
                "program_id": result.program_id,
                "confidence": result.confidence,
                "match_state": result.match_state,
            }
        )

        if result.emit_identified and result.program_id:
            self.cycle.program_identified_at = now.isoformat()
            self.cycle.events_emitted[EVENT_PROGRAM_IDENTIFIED] = True
            events.append(
                DetectorEvent(
                    name=EVENT_PROGRAM_IDENTIFIED,
                    data=self._cycle_event_data(),
                    shadow=self.config.shadow_mode,
                )
            )

        profile = self.profiles.get(result.program_id) if result.program_id else None
        progress, remaining, expected, eta_conf = compute_progress(
            started_at=self.cycle.started_at,
            now=now,
            profile=profile,
            program_match_state=result.match_state,
            current_progress=self.cycle.progress,
            internal_state=self.cycle.internal_state,
        )
        self.cycle.progress = progress
        self.cycle.time_remaining_seconds = remaining
        self.cycle.expected_completion_at = expected.isoformat() if expected else None
        self.cycle.eta_confidence = eta_conf

    def _update_availability(self, inp: DetectorInput) -> None:
        self.cycle.source_availability = {
            "power": inp.power_available,
            "energy": inp.energy_available,
            "door": inp.door_available,
            "movement": inp.movement_available,
        }
        if not inp.power_available:
            self.cycle.sensor_data_incomplete = True

    def _append_power_trace(self, inp: DetectorInput) -> None:
        if inp.power_w is None:
            return
        ts_key = inp.timestamp.isoformat()
        sample_key = (ts_key, inp.power_w)
        if self._last_power_sample == sample_key:
            return
        self._last_power_sample = sample_key

        last = self.cycle.trace_compact[-1] if self.cycle.trace_compact else None
        if last and last.get("power_w") == inp.power_w and last.get("timestamp") == ts_key:
            return

        point = {
            "timestamp": ts_key,
            "power_w": inp.power_w,
            "energy_wh": inp.energy_wh,
            "movement": inp.movement,
            "door_open": inp.door_open,
        }
        self.cycle.trace_compact.append(point)
        if len(self.cycle.trace_compact) > 2000:
            self.cycle.trace_compact = self.cycle.trace_compact[-2000:]

    def _cycle_event_data(self, **extra: Any) -> dict[str, Any]:
        from .const import PROGRAM_CATALOGUE

        pid = self.cycle.detected_program or self.cycle.selected_program
        expected = self.cycle.expected_completion_at
        return {
            "cycle_id": self.cycle.cycle_id,
            "program_id": pid,
            "program_name": PROGRAM_CATALOGUE.get(pid, pid) if pid and pid != "auto" else None,
            "program_source": self.cycle.program_source,
            "program_confidence": self.cycle.program_confidence,
            "eta_confidence": self.cycle.eta_confidence,
            "started_at": self.cycle.started_at,
            "expected_completion_at": expected,
            "completed_at": self.cycle.completed_at,
            "energy_wh": self.cycle.accumulated_energy_wh,
            "completion_reason": self.cycle.completion_reason,
            "restart_recovered": self.cycle.restart_recovered,
            "sensor_data_incomplete": self.cycle.sensor_data_incomplete,
            **extra,
        }

    def _begin_new_cycle(self, now: datetime, *, energy_at_start_wh: float | None = None) -> None:
        """Create a fresh cycle record for a new wash."""
        self.cycle = CycleRecord(cycle_id=str(uuid.uuid4()))
        self.cycle.start_candidate_at = now.isoformat()
        self._ensure_energy_baseline(energy_at_start_wh)
        self._last_power_sample = None
        self._energy_at_last_check = None
        self._energy_stable_since = None
        self.transitions = []

    def _ensure_energy_baseline(self, energy_wh: float | None) -> None:
        if energy_wh is not None and self.cycle.energy_at_start_wh is None:
            self.cycle.energy_at_start_wh = energy_wh

    def _update_energy_accumulation(self, inp: DetectorInput) -> None:
        if inp.energy_wh is None:
            return
        if self._energy_at_last_check is not None:
            if abs(inp.energy_wh - self._energy_at_last_check) < 0.01:
                if self._energy_stable_since is None:
                    self._energy_stable_since = inp.timestamp
            else:
                self._energy_stable_since = None
        self._energy_at_last_check = inp.energy_wh
        if self.cycle.energy_at_start_wh is not None:
            self.cycle.accumulated_energy_wh = max(
                0.0, inp.energy_wh - self.cycle.energy_at_start_wh
            )

    def _should_record_trace(self) -> bool:
        state = InternalState(self.cycle.internal_state)
        return state in (
            InternalState.START_CANDIDATE,
            InternalState.RUNNING,
            InternalState.PAUSED,
            InternalState.NEEDS_EMPTYING,
            InternalState.NEEDS_REWASH,
        )

    def set_energy_baseline(self, wh: float | None) -> None:
        """Set energy baseline at cycle start."""
        self.cycle.energy_at_start_wh = wh
