"""Domain models for WasherCycle (no Home Assistant imports)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from enum import StrEnum
except ImportError:

    class StrEnum(str, Enum):
        """StrEnum compatibility for Python < 3.11."""

        pass


from typing import Any


class InternalState(StrEnum):
    """Cycle detector internal states."""

    IDLE = "IDLE"
    START_CANDIDATE = "START_CANDIDATE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    END_CANDIDATE = "END_CANDIDATE"
    NEEDS_EMPTYING = "NEEDS_EMPTYING"
    NEEDS_REWASH = "NEEDS_REWASH"
    UNKNOWN = "UNKNOWN"


class PublicState(StrEnum):
    """Public-facing cycle states."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHING = "finishing"
    NEEDS_EMPTYING = "needs_emptying"
    NEEDS_REWASH = "needs_rewash"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


INTERNAL_TO_PUBLIC: dict[InternalState, PublicState] = {
    InternalState.IDLE: PublicState.IDLE,
    InternalState.START_CANDIDATE: PublicState.STARTING,
    InternalState.RUNNING: PublicState.RUNNING,
    InternalState.PAUSED: PublicState.RUNNING,
    InternalState.END_CANDIDATE: PublicState.FINISHING,
    InternalState.NEEDS_EMPTYING: PublicState.NEEDS_EMPTYING,
    InternalState.NEEDS_REWASH: PublicState.NEEDS_REWASH,
    InternalState.UNKNOWN: PublicState.UNAVAILABLE,
}


class SampleSource(StrEnum):
    """Which entity triggered a detector process call."""

    POWER = "power"
    ENERGY = "energy"
    DOOR = "door"
    MOVEMENT = "movement"
    PLUG = "plug"
    OTHER = "other"
    TICK = "tick"


class ProgramMatchState(StrEnum):
    """Program identification confidence levels."""

    UNKNOWN = "unknown"
    DETECTING = "detecting"
    TENTATIVE = "tentative"
    CONFIDENT = "confident"
    MANUAL = "manual"
    CORRECTED = "corrected"


class EtaConfidence(StrEnum):
    """ETA confidence labels."""

    UNKNOWN = "unknown"
    PROVISIONAL = "provisional"
    MATCHED = "matched"
    EXTENDED = "extended"
    UNAVAILABLE = "unavailable"


class SampleQuality(StrEnum):
    """Sample quality indicator."""

    OK = "ok"
    STALE = "stale"
    SPIKE = "spike"
    MISSING = "missing"
    REJECTED = "rejected"


class DoorCorrelationClass(StrEnum):
    """Door-open correlation classification."""

    MID_CYCLE = "mid_cycle"
    PENDING = "pending"
    IMMEDIATE_EMPTY = "immediate_empty"
    ORDINARY_UNLOAD = "ordinary_unload"


@dataclass
class NormalizedPower:
    """Normalized power reading."""

    timestamp: datetime
    watts: float
    quality: SampleQuality = SampleQuality.OK


@dataclass
class NormalizedEnergy:
    """Normalized cumulative energy reading (Wh)."""

    timestamp: datetime
    watt_hours: float
    quality: SampleQuality = SampleQuality.OK
    reset_detected: bool = False


@dataclass
class NormalizedBool:
    """Normalized boolean sensor reading."""

    timestamp: datetime
    value: bool
    quality: SampleQuality = SampleQuality.OK


@dataclass
class RejectedSample:
    """Rejected input sample with reason."""

    entity: str
    timestamp: datetime
    raw_value: str
    reason: str


@dataclass
class SourceAvailability:
    """Source entity availability snapshot."""

    power: bool = True
    energy: bool = True
    door: bool = True
    movement: bool = True
    plug_switch: bool = True


@dataclass
class ProgramCandidate:
    """Program match candidate."""

    program_id: str
    score: float
    energy_z: float = 0.0
    power_mae: float = 0.0


@dataclass
class CompactTracePoint:
    """Compact trace point for live cycle."""

    timestamp: str
    power_w: float | None = None
    energy_wh: float | None = None
    movement: bool | None = None
    door_open: bool | None = None


@dataclass
class CycleRecord:
    """Active or completed cycle record."""

    cycle_id: str
    internal_state: InternalState = InternalState.IDLE
    public_state: PublicState = PublicState.IDLE
    start_candidate_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    selected_program: str = "auto"
    detected_program: str | None = None
    program_confidence: float = 0.0
    program_source: str = "auto"
    program_match_state: ProgramMatchState = ProgramMatchState.UNKNOWN
    accumulated_energy_wh: float = 0.0
    trace_compact: list[dict[str, Any]] = field(default_factory=list)
    door_open_pending_at: str | None = None
    door_correlation_class: str | None = None
    end_candidate_at: str | None = None
    needs_emptying_at: str | None = None
    rewash_due_at: str | None = None
    restart_recovered: bool = False
    sensor_data_incomplete: bool = False
    source_availability: dict[str, bool] = field(default_factory=dict)
    state_reason: str = ""
    completion_reason: str = ""
    completion_detection_latency_seconds: float | None = None
    events_emitted: dict[str, bool] = field(default_factory=dict)
    energy_at_start_wh: float | None = None
    standby_since: str | None = None
    paused_at: str | None = None
    last_transition_at: str | None = None
    eta_confidence: str = EtaConfidence.UNKNOWN
    progress: float = 0.0
    expected_completion_at: str | None = None
    time_remaining_seconds: int | None = None
    calibration_program_id: str | None = None
    calibration_label_consumed: bool = False
    archive_pending: bool = False
    post_window_until: str | None = None
    program_identified_at: str | None = None
    completion_detected_at: str | None = None
    match_rejection_reason: str | None = None
    prediction_timeline: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "cycle_id": self.cycle_id,
            "internal_state": self.internal_state,
            "public_state": self.public_state,
            "start_candidate_at": self.start_candidate_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "selected_program": self.selected_program,
            "detected_program": self.detected_program,
            "program_confidence": self.program_confidence,
            "program_source": self.program_source,
            "program_match_state": self.program_match_state,
            "accumulated_energy_wh": self.accumulated_energy_wh,
            "trace_compact": self.trace_compact[-500:],
            "door_open_pending_at": self.door_open_pending_at,
            "door_correlation_class": self.door_correlation_class,
            "end_candidate_at": self.end_candidate_at,
            "needs_emptying_at": self.needs_emptying_at,
            "rewash_due_at": self.rewash_due_at,
            "restart_recovered": self.restart_recovered,
            "sensor_data_incomplete": self.sensor_data_incomplete,
            "source_availability": self.source_availability,
            "state_reason": self.state_reason,
            "completion_reason": self.completion_reason,
            "completion_detection_latency_seconds": self.completion_detection_latency_seconds,
            "events_emitted": self.events_emitted,
            "energy_at_start_wh": self.energy_at_start_wh,
            "standby_since": self.standby_since,
            "paused_at": self.paused_at,
            "last_transition_at": self.last_transition_at,
            "eta_confidence": self.eta_confidence,
            "progress": self.progress,
            "expected_completion_at": self.expected_completion_at,
            "time_remaining_seconds": self.time_remaining_seconds,
            "calibration_program_id": self.calibration_program_id,
            "calibration_label_consumed": self.calibration_label_consumed,
            "archive_pending": self.archive_pending,
            "post_window_until": self.post_window_until,
            "program_identified_at": self.program_identified_at,
            "completion_detected_at": self.completion_detected_at,
            "match_rejection_reason": self.match_rejection_reason,
            "prediction_timeline": self.prediction_timeline[-100:],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CycleRecord:
        """Deserialize from storage."""
        return cls(
            cycle_id=data["cycle_id"],
            internal_state=InternalState(data.get("internal_state", InternalState.IDLE)),
            public_state=PublicState(data.get("public_state", PublicState.IDLE)),
            start_candidate_at=data.get("start_candidate_at"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            selected_program=data.get("selected_program", "auto"),
            detected_program=data.get("detected_program"),
            program_confidence=float(data.get("program_confidence", 0.0)),
            program_source=data.get("program_source", "auto"),
            program_match_state=ProgramMatchState(
                data.get("program_match_state", ProgramMatchState.UNKNOWN)
            ),
            accumulated_energy_wh=float(data.get("accumulated_energy_wh", 0.0)),
            trace_compact=list(data.get("trace_compact", [])),
            door_open_pending_at=data.get("door_open_pending_at"),
            door_correlation_class=data.get("door_correlation_class"),
            end_candidate_at=data.get("end_candidate_at"),
            needs_emptying_at=data.get("needs_emptying_at"),
            rewash_due_at=data.get("rewash_due_at"),
            restart_recovered=bool(data.get("restart_recovered", False)),
            sensor_data_incomplete=bool(data.get("sensor_data_incomplete", False)),
            source_availability=dict(data.get("source_availability", {})),
            state_reason=data.get("state_reason", ""),
            completion_reason=data.get("completion_reason", ""),
            completion_detection_latency_seconds=data.get("completion_detection_latency_seconds"),
            events_emitted=dict(data.get("events_emitted", {})),
            energy_at_start_wh=data.get("energy_at_start_wh"),
            standby_since=data.get("standby_since"),
            paused_at=data.get("paused_at"),
            last_transition_at=data.get("last_transition_at"),
            eta_confidence=data.get("eta_confidence", EtaConfidence.UNKNOWN),
            progress=float(data.get("progress", 0.0)),
            expected_completion_at=data.get("expected_completion_at"),
            time_remaining_seconds=data.get("time_remaining_seconds"),
            calibration_program_id=data.get("calibration_program_id"),
            calibration_label_consumed=bool(data.get("calibration_label_consumed", False)),
            archive_pending=bool(data.get("archive_pending", False)),
            post_window_until=data.get("post_window_until"),
            program_identified_at=data.get("program_identified_at"),
            completion_detected_at=data.get("completion_detected_at"),
            match_rejection_reason=data.get("match_rejection_reason"),
            prediction_timeline=list(data.get("prediction_timeline", [])),
        )


@dataclass
class TrainingRun:
    """Saved training run."""

    run_id: str
    program_id: str
    program_name: str
    user_start_at: str
    user_complete_at: str
    observed_duration_seconds: float
    included_in_profile: bool = True
    confirmed: bool = True
    note: str = ""
    anomaly_flags: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    derived: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "run_id": self.run_id,
            "program_id": self.program_id,
            "program_name": self.program_name,
            "user_start_at": self.user_start_at,
            "user_complete_at": self.user_complete_at,
            "observed_duration_seconds": self.observed_duration_seconds,
            "included_in_profile": self.included_in_profile,
            "confirmed": self.confirmed,
            "note": self.note,
            "anomaly_flags": self.anomaly_flags,
            "raw": self.raw,
            "derived": self.derived,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrainingRun:
        """Deserialize from storage."""
        return cls(
            run_id=data["run_id"],
            program_id=data["program_id"],
            program_name=data["program_name"],
            user_start_at=data["user_start_at"],
            user_complete_at=data["user_complete_at"],
            observed_duration_seconds=float(data["observed_duration_seconds"]),
            included_in_profile=bool(data.get("included_in_profile", True)),
            confirmed=bool(data.get("confirmed", True)),
            note=data.get("note", ""),
            anomaly_flags=list(data.get("anomaly_flags", [])),
            raw=dict(data.get("raw", {})),
            derived=dict(data.get("derived", {})),
            schema_version=int(data.get("schema_version", 1)),
        )


@dataclass
class ProgramProfile:
    """Aggregated program profile."""

    program_id: str
    display_name: str
    accepted_run_ids: list[str] = field(default_factory=list)
    excluded_run_ids: list[str] = field(default_factory=list)
    confirmed_run_count: int = 0
    duration_median_seconds: float = 0.0
    duration_mad_seconds: float = 0.0
    energy_median_wh: float = 0.0
    energy_mad_wh: float = 0.0
    peak_power_median_w: float = 0.0
    mean_power_median_w: float = 0.0
    representative_trace: list[dict[str, Any]] = field(default_factory=list)
    power_envelope: dict[str, Any] = field(default_factory=dict)
    movement_envelope: list[dict[str, Any]] = field(default_factory=list)
    low_power_periods_typical: list[dict[str, Any]] = field(default_factory=list)
    major_transition_windows: list[dict[str, Any]] = field(default_factory=list)
    final_signature: dict[str, Any] = field(default_factory=dict)
    earliest_plausible_completion_seconds: float = 0.0
    earliest_identification_seconds: float = 0.0
    completion_detection_latency_median: float = 0.0
    last_rebuilt_at: str | None = None
    profile_schema_version: int = 2
    recognition_ready: bool = False
    real_run_count: int = 0
    feature_vector: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "program_id": self.program_id,
            "display_name": self.display_name,
            "accepted_run_ids": self.accepted_run_ids,
            "excluded_run_ids": self.excluded_run_ids,
            "confirmed_run_count": self.confirmed_run_count,
            "duration_median_seconds": self.duration_median_seconds,
            "duration_mad_seconds": self.duration_mad_seconds,
            "energy_median_wh": self.energy_median_wh,
            "energy_mad_wh": self.energy_mad_wh,
            "peak_power_median_w": self.peak_power_median_w,
            "mean_power_median_w": self.mean_power_median_w,
            "representative_trace": self.representative_trace,
            "power_envelope": self.power_envelope,
            "movement_envelope": self.movement_envelope,
            "low_power_periods_typical": self.low_power_periods_typical,
            "major_transition_windows": self.major_transition_windows,
            "final_signature": self.final_signature,
            "earliest_plausible_completion_seconds": self.earliest_plausible_completion_seconds,
            "earliest_identification_seconds": self.earliest_identification_seconds,
            "completion_detection_latency_median": self.completion_detection_latency_median,
            "last_rebuilt_at": self.last_rebuilt_at,
            "profile_schema_version": self.profile_schema_version,
            "recognition_ready": self.recognition_ready,
            "real_run_count": self.real_run_count,
            "feature_vector": self.feature_vector,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProgramProfile:
        """Deserialize from storage."""
        return cls(
            program_id=data["program_id"],
            display_name=data["display_name"],
            accepted_run_ids=list(data.get("accepted_run_ids", [])),
            excluded_run_ids=list(data.get("excluded_run_ids", [])),
            confirmed_run_count=int(data.get("confirmed_run_count", 0)),
            duration_median_seconds=float(data.get("duration_median_seconds", 0.0)),
            duration_mad_seconds=float(data.get("duration_mad_seconds", 0.0)),
            energy_median_wh=float(data.get("energy_median_wh", 0.0)),
            energy_mad_wh=float(data.get("energy_mad_wh", 0.0)),
            peak_power_median_w=float(data.get("peak_power_median_w", 0.0)),
            mean_power_median_w=float(data.get("mean_power_median_w", 0.0)),
            representative_trace=list(data.get("representative_trace", [])),
            power_envelope=dict(data.get("power_envelope", {})),
            movement_envelope=list(data.get("movement_envelope", [])),
            low_power_periods_typical=list(data.get("low_power_periods_typical", [])),
            major_transition_windows=list(data.get("major_transition_windows", [])),
            final_signature=dict(data.get("final_signature", {})),
            earliest_plausible_completion_seconds=float(
                data.get("earliest_plausible_completion_seconds", 0.0)
            ),
            earliest_identification_seconds=float(data.get("earliest_identification_seconds", 0.0)),
            completion_detection_latency_median=float(
                data.get("completion_detection_latency_median", 0.0)
            ),
            last_rebuilt_at=data.get("last_rebuilt_at"),
            profile_schema_version=int(data.get("profile_schema_version", 1)),
            recognition_ready=bool(data.get("recognition_ready", False)),
            real_run_count=int(data.get("real_run_count", 0)),
            feature_vector=dict(data.get("feature_vector", {})),
        )


@dataclass
class DetectorConfig:
    """Runtime detector configuration."""

    start_power_w: float = 19.0
    standby_power_w: float = 5.0
    start_sustain_seconds: float = 30.0
    start_min_energy_wh: float = 1.0
    fallback_completion_seconds: float = 300.0
    early_completion_enabled: bool = True
    early_completion_min_score: float = 0.75
    door_correlation_seconds: float = 30.0
    movement_enabled: bool = True
    max_stale_seconds: float = 120.0
    shadow_mode: bool = True
    early_confirm_seconds: float = 8.0
    impossible_spike_w: float = 3000.0
    provisional_min_duration_seconds: float = 900.0
    min_runs_recognition: int = 3
    min_runs_robust: int = 5
    resample_interval_seconds: int = 15
    matcher_margin: float = 0.12
    rewash_delay_minutes: int = 120
    standby_confirm_seconds: float = 60.0
    post_completion_seconds: int = 30


@dataclass
class StateTransition:
    """Recorded state transition for diagnostics."""

    timestamp: str
    from_state: str
    to_state: str
    reason: str
    event: str | None = None


@dataclass
class LatencyStats:
    """Completion detection latency statistics."""

    median_seconds: float = 0.0
    p90_seconds: float = 0.0
    slowest_seconds: float = 0.0
    count_over_target: int = 0
    false_early_count: int = 0
    samples: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "median_seconds": self.median_seconds,
            "p90_seconds": self.p90_seconds,
            "slowest_seconds": self.slowest_seconds,
            "count_over_target": self.count_over_target,
            "false_early_count": self.false_early_count,
            "samples": self.samples[-100:],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LatencyStats:
        """Deserialize from storage."""
        return cls(
            median_seconds=float(data.get("median_seconds", 0.0)),
            p90_seconds=float(data.get("p90_seconds", 0.0)),
            slowest_seconds=float(data.get("slowest_seconds", 0.0)),
            count_over_target=int(data.get("count_over_target", 0)),
            false_early_count=int(data.get("false_early_count", 0)),
            samples=list(data.get("samples", [])),
        )
