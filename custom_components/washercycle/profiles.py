"""Program profile building for WasherCycle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .const import PROGRAM_CATALOGUE
from .models import ProgramProfile, TrainingRun
from .stats import mad, median


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _resample_power(
    power_samples: list[dict[str, Any]], interval_seconds: int
) -> list[dict[str, Any]]:
    """Resample irregular power trace to fixed interval."""
    if not power_samples:
        return []
    start = _parse_ts(power_samples[0]["t"])
    end = _parse_ts(power_samples[-1]["t"])
    duration = (end - start).total_seconds()
    if duration <= 0:
        return [{"offset_s": 0, "w": power_samples[0].get("w", 0)}]

    result: list[dict[str, Any]] = []
    idx = 0
    offset = 0.0
    while offset <= duration:
        target = start.timestamp() + offset
        while idx < len(power_samples) - 1:
            ts = _parse_ts(power_samples[idx + 1]["t"]).timestamp()
            if ts > target:
                break
            idx += 1
        result.append({"offset_s": offset, "w": power_samples[idx].get("w", 0)})
        offset += interval_seconds
    return result


def _extract_final_signature(
    power_samples: list[dict[str, Any]],
    complete_at: str,
    pre_seconds: int,
    post_seconds: int,
) -> dict[str, Any]:
    """Extract final signature window around marked completion."""
    complete_ts = _parse_ts(complete_at).timestamp()
    pre_start = complete_ts - pre_seconds
    post_end = complete_ts + post_seconds
    pre_window = []
    post_window = []
    for s in power_samples:
        ts = _parse_ts(s["t"]).timestamp()
        if pre_start <= ts <= complete_ts:
            pre_window.append({"offset_s": ts - complete_ts, "w": s.get("w", 0)})
        elif complete_ts < ts <= post_end:
            post_window.append({"offset_s": ts - complete_ts, "w": s.get("w", 0)})
    return {"pre_window": pre_window, "post_window": post_window}


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
    excluded_ids = [r.run_id for r in runs if not r.included_in_profile and r.program_id == program_id]

    profile = ProgramProfile(
        program_id=program_id,
        display_name=display_name,
        accepted_run_ids=[r.run_id for r in accepted],
        excluded_run_ids=excluded_ids,
        confirmed_run_count=len(accepted),
        last_rebuilt_at=datetime.now(timezone.utc).isoformat(),
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

    if latencies:
        profile.completion_detection_latency_median = median(latencies)

    profile.earliest_plausible_completion_seconds = profile.duration_median_seconds * 0.6
    profile.earliest_identification_seconds = profile.duration_median_seconds * 0.15

    resampled_traces = []
    final_signatures = []
    for run in accepted:
        power = run.raw.get("power", [])
        if power:
            resampled_traces.append(_resample_power(power, resample_interval_seconds))
            final_signatures.append(
                _extract_final_signature(
                    power,
                    run.user_complete_at,
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
                rep_trace.append(
                    {"offset_s": i * resample_interval_seconds, "w": median(vals)}
                )
        profile.representative_trace = rep_trace

        times = list(range(max_len))
        p10, p50, p90 = [], [], []
        for i in range(max_len):
            vals = sorted(t[i]["w"] for t in resampled_traces if i < len(t))
            if vals:
                n = len(vals)
                p10.append(vals[max(0, int(n * 0.1))])
                p50.append(median(vals))
                p90.append(vals[min(n - 1, int(n * 0.9))])
        profile.power_envelope = {
            "times": [t * resample_interval_seconds for t in times[: len(p50)]],
            "p10": p10,
            "p50": p50,
            "p90": p90,
        }

    if final_signatures:
        pre_lens = [len(s.get("pre_window", [])) for s in final_signatures]
        if pre_lens:
            min_pre = min(pre_lens)
            merged_pre = []
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
            profile.final_signature = {"pre_window": merged_pre, "post_window": []}

    return profile


def seed_profiles() -> dict[str, ProgramProfile]:
    """Create empty profiles for all catalogue programs."""
    return {
        pid: ProgramProfile(program_id=pid, display_name=name)
        for pid, name in PROGRAM_CATALOGUE.items()
    }
