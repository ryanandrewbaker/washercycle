"""Program profile building for WasherCycle."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .const import PROGRAM_CATALOGUE
from .models import ProgramProfile, TrainingRun
from .preset import APPLIANCE_PRESET
from .resample import _extract_final_signature_impl, parse_ts, resample_trace
from .stats import mad, median


def _power_samples_from_run(run: TrainingRun) -> list[dict[str, Any]]:
    return run.raw.get("power", [])


def _extract_final_signature(
    power_samples: list[dict[str, Any]],
    complete_at: str,
    pre_seconds: int,
    post_seconds: int,
) -> dict[str, Any]:
    return _extract_final_signature_impl(power_samples, complete_at, pre_seconds, post_seconds)


def _count_real_runs(runs: list[TrainingRun]) -> int:
    return sum(
        1
        for r in runs
        if r.schema_version >= 2
        and "manual_timing" not in r.anomaly_flags
        and "unlabelled_program" not in r.anomaly_flags
        and r.included_in_profile
        and r.derived.get("quality") in ("auto", "calibration_label", None)
    )


def build_profile_from_runs(
    program_id: str,
    runs: list[TrainingRun],
    *,
    resample_interval_seconds: int = 15,
    end_signature_pre_seconds: int = 300,
    end_signature_post_seconds: int = 30,
) -> ProgramProfile:
    """Build or rebuild a program profile from accepted training runs."""
    display_name = PROGRAM_CATALOGUE.get(program_id, program_id)
    accepted = [r for r in runs if r.included_in_profile and r.program_id == program_id]
    excluded_ids = [
        r.run_id for r in runs if not r.included_in_profile and r.program_id == program_id
    ]
    real_runs = [
        r
        for r in accepted
        if "manual_timing" not in r.anomaly_flags
        and "unlabelled_program" not in r.anomaly_flags
        and r.derived.get("quality") != "synthetic"
    ]

    profile = ProgramProfile(
        program_id=program_id,
        display_name=display_name,
        accepted_run_ids=[r.run_id for r in accepted],
        excluded_run_ids=excluded_ids,
        confirmed_run_count=len(accepted),
        real_run_count=len(real_runs),
        recognition_ready=len(real_runs) >= int(APPLIANCE_PRESET["min_real_runs_recognition"]),
        last_rebuilt_at=datetime.now(UTC).isoformat(),
        profile_schema_version=2,
    )

    if not accepted:
        return profile

    durations = [r.observed_duration_seconds for r in accepted]
    energies = [r.derived.get("cycle_energy_wh", 0.0) for r in accepted]
    peaks = [r.derived.get("peak_power_w", 0.0) for r in accepted]
    means = [r.derived.get("mean_power_w", 0.0) for r in accepted]
    latencies = [
        r.derived["completion_latency_seconds"]
        for r in accepted
        if r.derived.get("completion_latency_seconds") is not None
    ]

    profile.duration_median_seconds = median(durations)
    profile.duration_mad_seconds = mad(durations, profile.duration_median_seconds)
    profile.energy_median_wh = median(energies)
    profile.energy_mad_wh = mad(energies, profile.energy_median_wh)
    profile.peak_power_median_w = median(peaks)
    profile.mean_power_median_w = median(means)
    profile.feature_vector = {
        "peak_power_w": profile.peak_power_median_w,
        "mean_power_w": profile.mean_power_median_w,
        "energy_median_wh": profile.energy_median_wh,
    }

    if latencies:
        profile.completion_detection_latency_median = median(latencies)

    profile.earliest_plausible_completion_seconds = profile.duration_median_seconds * 0.6
    profile.earliest_identification_seconds = profile.duration_median_seconds * 0.15

    resampled_traces = []
    final_signatures = []
    for run in accepted:
        power = _power_samples_from_run(run)
        if power:
            start = run.derived.get("auto_detected_start_at") or run.user_start_at
            origin = parse_ts(start)
            resampled_traces.append(
                resample_trace(power, origin=origin, interval_s=resample_interval_seconds)
            )
            complete = run.derived.get("auto_detected_complete_at") or run.user_complete_at
            final_signatures.append(
                _extract_final_signature(
                    power,
                    complete,
                    end_signature_pre_seconds,
                    end_signature_post_seconds,
                )
            )

    if resampled_traces:
        max_len = max(len(t) for t in resampled_traces)
        rep_trace = []
        for i in range(max_len):
            vals = [t[i]["w"] for t in resampled_traces if i < len(t)]
            if vals:
                rep_trace.append({"offset_s": i * resample_interval_seconds, "w": median(vals)})
        profile.representative_trace = rep_trace

        p10, p50, p90 = [], [], []
        for i in range(max_len):
            vals = sorted(t[i]["w"] for t in resampled_traces if i < len(t))
            if vals:
                n = len(vals)
                p10.append(vals[max(0, int(n * 0.1))])
                p50.append(median(vals))
                p90.append(vals[min(n - 1, int(n * 0.9))])
        profile.power_envelope = {
            "times": [i * resample_interval_seconds for i in range(len(p50))],
            "p10": p10,
            "p50": p50,
            "p90": p90,
        }

    if final_signatures:
        pre_lens = [len(s.get("pre_window", [])) for s in final_signatures]
        post_lens = [len(s.get("post_window", [])) for s in final_signatures]
        merged_pre, merged_post = [], []
        if pre_lens:
            min_pre = min(pre_lens)
            for i in range(min_pre):
                vals = []
                for sig in final_signatures:
                    pw = sig.get("pre_window", [])
                    if i < len(pw):
                        vals.append(pw[i]["w"])
                if vals:
                    merged_pre.append(
                        {
                            "offset_s": final_signatures[0]["pre_window"][i]["offset_s"],
                            "w": median(vals),
                        }
                    )
        if post_lens:
            min_post = min(post_lens)
            for i in range(min_post):
                vals = []
                for sig in final_signatures:
                    pw = sig.get("post_window", [])
                    if i < len(pw):
                        vals.append(pw[i]["w"])
                if vals:
                    merged_post.append(
                        {
                            "offset_s": final_signatures[0]["post_window"][i]["offset_s"],
                            "w": median(vals),
                        }
                    )
        profile.final_signature = {"pre_window": merged_pre, "post_window": merged_post}

    return profile


def seed_profiles() -> dict[str, ProgramProfile]:
    """Create empty profiles for all catalogue programs."""
    return {
        pid: ProgramProfile(program_id=pid, display_name=name, profile_schema_version=2)
        for pid, name in PROGRAM_CATALOGUE.items()
    }
