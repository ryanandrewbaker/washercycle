"""Cycle detector state machine for WasherCycle."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .evidence import correlated_door_completion_threshold, score_completion_evidence
from .matcher import match_program
from .models import (
    INTERNAL_TO_PUBLIC,
    CycleRecord,
    DetectorConfig,
    DoorCorrelationClass,
    InternalState,
    ProgramMatchState,
    PublicState,
    StateTransition,
)
from .progress import compute_progress


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@dataclass
class DetectorEvent:
    """Event emitted by detector."""

    name: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectorResult:
    """Result of processing an input."""

    cycle: CycleRecord
    events: list[DetectorEvent] = field(default_factory=list)
    transitions: list[StateTransition] = field(default_factory=list)
    announcement_requests: list[str] = field(default_factory=list)


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


class CycleDetector:
    """Pure Python cycle state machine."""

    def __init__(
        self,
        config: DetectorConfig,
        cycle: CycleRecord | None = None,
        profiles: dict | None = None,
        pending_program: str = "auto",
    ) -> None:
        self.config = config
        self.cycle = cycle or CycleRecord(cycle_id=str(uuid.uuid4()))
        self.profiles = profiles or {}
        self.pending_program = pending_program
        self.transitions: list[StateTransition] = []
        self._energy_at_last_check: float | None = None
        self._energy_stable_since: datetime | None = None

    def restore(self, cycle: CycleRecord, pending_program: str = "auto") -> None:
        """Restore detector from persisted cycle."""
        self.cycle = cycle
        self.cycle.restart_recovered = True
        self.pending_program = pending_program

    def process(self, inp: DetectorInput) -> DetectorResult:
        """Process one normalised input."""
        events: list[DetectorEvent] = []
        announcements: list[str] = []
        now = inp.timestamp

        self._update_availability(inp)
        self._append_trace(inp)

        if inp.energy_wh is not None:
            if self._energy_at_last_check is not None:
                if abs(inp.energy_wh - self._energy_at_last_check) < 0.01:
                    if self._energy_stable_since is None:
                        self._energy_stable_since = now
                else:
                    self._energy_stable_since = None
            self._energy_at_last_check = inp.energy_wh

        state = InternalState(self.cycle.internal_state)

        if state == InternalState.IDLE:
            events, announcements = self._handle_idle(inp, events, announcements)
        elif state == InternalState.START_CANDIDATE:
            events, announcements = self._handle_start_candidate(inp, events, announcements)
        elif state in (InternalState.RUNNING, InternalState.PAUSED):
            events, announcements = self._handle_running(inp, events, announcements)
        elif state == InternalState.END_CANDIDATE:
            events, announcements = self._handle_end_candidate(inp, events, announcements)
        elif state == InternalState.NEEDS_EMPTYING:
            events, announcements = self._handle_needs_emptying(inp, events, announcements)
        elif state == InternalState.NEEDS_REWASH:
            events, announcements = self._handle_needs_rewash(inp, events, announcements)

        if self.cycle.door_open_pending_at and state not in (
            InternalState.IDLE,
            InternalState.NEEDS_EMPTYING,
            InternalState.NEEDS_REWASH,
        ):
            events, announcements = self._handle_door_correlation(inp, events, announcements)

        self._update_matching(now)
        return DetectorResult(
            cycle=self.cycle,
            events=events,
            transitions=self.transitions[-10:],
            announcement_requests=announcements,
        )

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
        self.cycle.public_state = INTERNAL_TO_PUBLIC.get(to_state, PublicState.UNKNOWN)
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
            return DetectorEvent(name=event, data=event_data or {})
        return None

    def _handle_idle(
        self, inp: DetectorInput, events: list, announcements: list
    ) -> tuple[list, list]:
        if inp.power_w is None or not inp.power_available:
            return events, announcements
        if inp.power_w < self.config.start_power_w:
            return events, announcements
        if inp.door_open is True:
            return events, announcements

        now = inp.timestamp
        self.cycle.start_candidate_at = now.isoformat()
        self.cycle.cycle_id = str(uuid.uuid4())
        evt = self._transition(
            InternalState.START_CANDIDATE, "power_above_threshold", now
        )
        if evt:
            events.append(evt)
        return events, announcements

    def _handle_start_candidate(
        self, inp: DetectorInput, events: list, announcements: list
    ) -> tuple[list, list]:
        now = inp.timestamp
        if not self.cycle.start_candidate_at:
            return events, announcements

        candidate_start = _parse_ts(self.cycle.start_candidate_at)
        elapsed = (now - candidate_start).total_seconds()

        if inp.door_open is True or (inp.power_w is not None and inp.power_w < self.config.start_power_w):
            if elapsed < self.config.start_sustain_seconds:
                evt = self._transition(InternalState.IDLE, "start_candidate_cancelled", now)
                self.cycle.start_candidate_at = None
                if evt:
                    events.append(evt)
                return events, announcements

        if inp.power_w is not None and inp.power_w >= self.config.start_power_w:
            if elapsed >= self.config.start_sustain_seconds:
                energy_ok = True
                if inp.energy_wh is not None and self.cycle.energy_at_start_wh is not None:
                    delta = inp.energy_wh - self.cycle.energy_at_start_wh
                    energy_ok = delta >= self.config.start_min_energy_wh or elapsed >= self.config.start_sustain_seconds * 2

                if energy_ok or inp.energy_wh is None:
                    self.cycle.started_at = now.isoformat()
                    selected = self.pending_program if self.pending_program != "auto" else "auto"
                    self.cycle.selected_program = selected
                    if selected != "auto":
                        self.cycle.detected_program = selected
                        self.cycle.program_source = "manual"
                        self.cycle.program_match_state = ProgramMatchState.MANUAL
                    self.cycle.energy_at_start_wh = inp.energy_wh
                    evt = self._transition(
                        InternalState.RUNNING,
                        "cycle_confirmed_start",
                        now,
                        event="washercycle_cycle_started",
                        event_data=self._cycle_event_data(),
                    )
                    if evt:
                        events.append(evt)
        return events, announcements

    def _handle_running(
        self, inp: DetectorInput, events: list, announcements: list
    ) -> tuple[list, list]:
        now = inp.timestamp
        state = InternalState(self.cycle.internal_state)

        if inp.power_w is not None and inp.power_w < self.config.standby_power_w:
            if not self.cycle.standby_since:
                self.cycle.standby_since = now.isoformat()
            standby_elapsed = (now - _parse_ts(self.cycle.standby_since)).total_seconds()
            if standby_elapsed >= self.config.fallback_completion_seconds:
                return self._complete_cycle(
                    now, "fallback_timeout", events, announcements, immediate_empty=False
                )
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

        evidence = self._score_evidence(now, inp)
        self.cycle.pending_end_evidence = evidence.to_dict()

        if self.config.early_completion_enabled and evidence.total >= self.config.early_completion_min_score:
            if not evidence.contradictory:
                self.cycle.end_candidate_at = now.isoformat()
                evt = self._transition(InternalState.END_CANDIDATE, "evidence_threshold_met", now)
                if evt:
                    events.append(evt)

        return events, announcements

    def _handle_end_candidate(
        self, inp: DetectorInput, events: list, announcements: list
    ) -> tuple[list, list]:
        now = inp.timestamp
        evidence = self._score_evidence(now, inp)
        self.cycle.pending_end_evidence = evidence.to_dict()

        if evidence.contradictory:
            self.cycle.end_candidate_at = None
            self.cycle.standby_since = None
            evt = self._transition(
                InternalState.RUNNING if inp.power_w and inp.power_w >= self.config.standby_power_w else InternalState.PAUSED,
                "end_candidate_cancelled",
                now,
            )
            if evt:
                events.append(evt)
            return events, announcements

        if not self.cycle.end_candidate_at:
            return events, announcements

        candidate_elapsed = (now - _parse_ts(self.cycle.end_candidate_at)).total_seconds()
        if candidate_elapsed >= self.config.early_confirm_seconds:
            if evidence.total >= 0.65:
                return self._complete_cycle(
                    now, "early_evidence_confirmed", events, announcements
                )

        if inp.power_w is not None and inp.power_w < self.config.standby_power_w:
            if self.cycle.standby_since:
                standby_elapsed = (now - _parse_ts(self.cycle.standby_since)).total_seconds()
                if standby_elapsed >= self.config.fallback_completion_seconds:
                    return self._complete_cycle(
                        now, "fallback_timeout", events, announcements
                    )

        return events, announcements

    def _handle_needs_emptying(
        self, inp: DetectorInput, events: list, announcements: list
    ) -> tuple[list, list]:
        now = inp.timestamp

        if inp.door_open is True:
            return self._empty_cycle(now, events, announcements)

        if self.cycle.rewash_due_at and now >= _parse_ts(self.cycle.rewash_due_at):
            evt = self._transition(
                InternalState.NEEDS_REWASH,
                "rewash_delay_expired",
                now,
                event="washercycle_needs_rewash",
                event_data=self._cycle_event_data(),
            )
            if evt:
                events.append(evt)
            announcements.append("rewash")

        return events, announcements

    def _handle_needs_rewash(
        self, inp: DetectorInput, events: list, announcements: list
    ) -> tuple[list, list]:
        now = inp.timestamp
        if inp.door_open is True:
            return self._empty_cycle(now, events, announcements)
        return events, announcements

    def _handle_door_correlation(
        self, inp: DetectorInput, events: list, announcements: list
    ) -> tuple[list, list]:
        now = inp.timestamp
        if not self.cycle.door_open_pending_at:
            return events, announcements

        door_open = _parse_ts(self.cycle.door_open_pending_at)
        window = self.config.door_correlation_seconds
        if (now - door_open).total_seconds() > window:
            self.cycle.door_correlation_class = DoorCorrelationClass.MID_CYCLE.value
            self.cycle.door_open_pending_at = None
            return events, announcements

        evidence = self._score_evidence(now, inp)
        threshold = correlated_door_completion_threshold()
        if evidence.total >= threshold and not evidence.contradictory:
            self.cycle.door_correlation_class = DoorCorrelationClass.IMMEDIATE_EMPTY.value
            return self._complete_cycle(
                now,
                "door_correlated_completion",
                events,
                announcements,
                immediate_empty=True,
            )

        return events, announcements

    def _complete_cycle(
        self,
        now: datetime,
        reason: str,
        events: list,
        announcements: list,
        *,
        immediate_empty: bool = False,
    ) -> tuple[list, list]:
        self.cycle.completed_at = now.isoformat()
        self.cycle.completion_reason = reason
        self.cycle.immediately_emptied = immediate_empty

        evt = DetectorEvent(
            name="washercycle_cycle_completed",
            data=self._cycle_event_data(
                completion_reason=reason,
                immediately_emptied=immediate_empty,
            ),
        )
        if not self.cycle.events_emitted.get("washercycle_cycle_completed"):
            self.cycle.events_emitted["washercycle_cycle_completed"] = True
            events.append(evt)

        if immediate_empty:
            self.cycle.door_correlation_class = DoorCorrelationClass.IMMEDIATE_EMPTY.value
            empty_evt = DetectorEvent(
                name="washercycle_cycle_emptied",
                data=self._cycle_event_data(immediately_emptied=True),
            )
            if not self.cycle.events_emitted.get("washercycle_cycle_emptied"):
                self.cycle.events_emitted["washercycle_cycle_emptied"] = True
                events.append(empty_evt)
            self._transition(InternalState.IDLE, "completed_and_emptied", now)
            self.cycle.progress = 100.0
            return events, announcements

        self.cycle.needs_emptying_at = now.isoformat()
        rewash_due = now + timedelta(minutes=self.config.rewash_delay_minutes)
        self.cycle.rewash_due_at = rewash_due.isoformat()
        self._transition(InternalState.NEEDS_EMPTYING, reason, now)
        self.cycle.progress = 100.0

        if not self.config.shadow_mode:
            announcements.append("completion")

        return events, announcements

    def _empty_cycle(
        self, now: datetime, events: list, announcements: list
    ) -> tuple[list, list]:
        self.cycle.door_correlation_class = DoorCorrelationClass.ORDINARY_UNLOAD.value
        evt = DetectorEvent(
            name="washercycle_cycle_emptied",
            data=self._cycle_event_data(),
        )
        if not self.cycle.events_emitted.get("washercycle_cycle_emptied"):
            self.cycle.events_emitted["washercycle_cycle_emptied"] = True
            events.append(evt)
        self._transition(InternalState.IDLE, "door_opened_emptied", now)
        return events, announcements

    def force_empty(self, now: datetime | None = None) -> DetectorResult:
        """Manually force cycle to empty/idle."""
        now = now or datetime.now(timezone.utc)
        events = []
        evt = DetectorEvent(name="washercycle_cycle_emptied", data=self._cycle_event_data())
        self.cycle.events_emitted["washercycle_cycle_emptied"] = True
        events.append(evt)
        self._transition(InternalState.IDLE, "manual_force_empty", now)
        return DetectorResult(cycle=self.cycle, events=events)

    def _score_evidence(self, now: datetime, inp: DetectorInput) -> Any:
        elapsed = 0.0
        if self.cycle.started_at:
            elapsed = (now - _parse_ts(self.cycle.started_at)).total_seconds()

        profile = None
        if self.cycle.detected_program:
            profile = self.profiles.get(self.cycle.detected_program)

        energy_stable = False
        if self._energy_stable_since:
            energy_stable = (now - self._energy_stable_since).total_seconds() >= 60

        energy_wh = 0.0
        if inp.energy_wh is not None and self.cycle.energy_at_start_wh is not None:
            energy_wh = max(0.0, inp.energy_wh - self.cycle.energy_at_start_wh)

        return score_completion_evidence(
            now=now,
            elapsed_seconds=elapsed,
            current_power_w=inp.power_w,
            movement_active=inp.movement,
            energy_wh=energy_wh,
            energy_stable=energy_stable,
            trace=self.cycle.trace_compact,
            profile=profile,
            config=self.config,
            movement_available=inp.movement_available,
        )

    def _update_matching(self, now: datetime) -> None:
        if InternalState(self.cycle.internal_state) not in (
            InternalState.RUNNING,
            InternalState.PAUSED,
            InternalState.END_CANDIDATE,
        ):
            return
        if not self.cycle.started_at:
            return

        elapsed = (now - _parse_ts(self.cycle.started_at)).total_seconds()
        energy_wh = self.cycle.accumulated_energy_wh

        manual = self.cycle.selected_program if self.cycle.program_source == "manual" else None
        pid, conf, match_state, _ = match_program(
            elapsed_seconds=elapsed,
            energy_wh=energy_wh,
            trace=self.cycle.trace_compact,
            profiles=self.profiles,
            config=self.config,
            manual_program=manual,
            current_match=self.cycle.detected_program,
            current_state=ProgramMatchState(self.cycle.program_match_state),
        )

        if pid:
            self.cycle.detected_program = pid
        self.cycle.program_confidence = conf
        self.cycle.program_match_state = match_state

        profile = self.profiles.get(pid) if pid else None
        progress, remaining, expected, eta_conf = compute_progress(
            started_at=self.cycle.started_at,
            now=now,
            profile=profile,
            program_match_state=match_state,
            current_progress=self.cycle.progress,
            internal_state=self.cycle.internal_state,
            immediately_emptied=self.cycle.immediately_emptied,
        )
        self.cycle.progress = progress
        self.cycle.time_remaining_seconds = remaining
        self.cycle.expected_completion_at = expected
        self.cycle.eta_confidence = eta_conf

    def _update_availability(self, inp: DetectorInput) -> None:
        self.cycle.source_availability = {
            "power": inp.power_available,
            "energy": inp.energy_available,
            "door": inp.door_available,
            "movement": inp.movement_available,
        }
        if not all([inp.power_available, inp.energy_available]):
            self.cycle.sensor_data_incomplete = True

    def _append_trace(self, inp: DetectorInput) -> None:
        point = {
            "timestamp": inp.timestamp.isoformat(),
            "power_w": inp.power_w,
            "energy_wh": inp.energy_wh,
            "movement": inp.movement,
            "door_open": inp.door_open,
        }
        self.cycle.trace_compact.append(point)
        if len(self.cycle.trace_compact) > 2000:
            self.cycle.trace_compact = self.cycle.trace_compact[-2000:]

        if inp.energy_wh is not None and self.cycle.energy_at_start_wh is not None:
            self.cycle.accumulated_energy_wh = max(
                0.0, inp.energy_wh - self.cycle.energy_at_start_wh
            )

    def _cycle_event_data(self, **extra: Any) -> dict[str, Any]:
        from .const import PROGRAM_CATALOGUE

        pid = self.cycle.detected_program or self.cycle.selected_program
        return {
            "cycle_id": self.cycle.cycle_id,
            "program_id": pid,
            "program_name": PROGRAM_CATALOGUE.get(pid, pid) if pid and pid != "auto" else None,
            "program_source": self.cycle.program_source,
            "program_confidence": self.cycle.program_confidence,
            "eta_confidence": self.cycle.eta_confidence,
            "started_at": self.cycle.started_at,
            "completed_at": self.cycle.completed_at,
            "energy_wh": self.cycle.accumulated_energy_wh,
            "completion_reason": self.cycle.completion_reason,
            "immediately_emptied": self.cycle.immediately_emptied,
            "door_opened_at": self.cycle.door_open_pending_at,
            "restart_recovered": self.cycle.restart_recovered,
            "sensor_data_incomplete": self.cycle.sensor_data_incomplete,
            **extra,
        }

    def set_energy_baseline(self, wh: float | None) -> None:
        """Set energy baseline at cycle start."""
        self.cycle.energy_at_start_wh = wh
