# WasherCycle v1 → v2 → v3 Migration

## Overview

Version 2.0 refocuses WasherCycle on the Samsung WW75J54E0IW/SA with automatic cycle
recording, time-aligned matching, and notifications handled by the Home Assistant package.

Version 2.1.0 (storage v3) fixes cycle isolation, energy capture, and completion
archiving. It intentionally resets unreliable learning data from v2.0.4 installs while
preserving your config entry and source sensors.

## Rollout order

1. Install v2.1 in **shadow mode** (default on).
2. Collect and replay real traces; review diagnostics metrics.
3. Validate state, programme, ETA, completion, and door behaviour.
4. Install `examples/packages/washercycle_notifications.yaml`.
5. Remove legacy washer automations.
6. Disable shadow mode.
7. Re-calibrate programmes using `select.washercycle_next_program`.

## Shadow mode

While shadow mode is enabled, operational events (`cycle_completed`, `cycle_emptied`,
`needs_rewash`, `program_identified`) are **not fired**. The notification package will
not receive duplicate notifications alongside legacy automations.

## Entity changes

Removed from the integration (use diagnostics download instead):

- Training/recording buttons and sensors
- `binary_sensor.washercycle_recording`
- `binary_sensor.washercycle_needs_rewash` (state still on `sensor.washercycle_state`)
- Announcement/TTS options

Renamed select (unique ID preserved):

- `select.washercycle_program_select` → `select.washercycle_next_program`

Stable contract entities (12 total):

- `sensor.washercycle_state`, `sensor.washercycle_program`, `sensor.washercycle_progress`
- `sensor.washercycle_time_remaining`, `sensor.washercycle_expected_completion`
- `sensor.washercycle_last_cycle_duration`, `sensor.washercycle_last_cycle_energy`
- `sensor.washercycle_program_confidence`, `sensor.washercycle_eta_confidence`
- `binary_sensor.washercycle_running`, `binary_sensor.washercycle_needs_emptying`
- `select.washercycle_next_program`

Obsolete entity registry entries are removed automatically on setup.

## Storage migration

Storage automatically migrates on load via Home Assistant's Store migration callback:

**v1 → v2**

- Removes `announcement_state` and `active_recording`
- Flags manual-timing runs with `manual_timing` anomaly
- Rebuilds profile schema with `recognition_ready` gates

**v2 → v3 (v2.1.0)**

- Resets `training_runs`, `completed_history`, and active cycle state
- Reseeds programme profiles from defaults
- Sets `pending_program` to `auto`
- Preserves `config_entry_id` and normalizer state

Back up `.storage/washercycle.storage_*` before upgrading.

## Rollback

1. Stop Home Assistant.
2. Restore storage backup.
3. Reinstall the previous WasherCycle version via HACS.
4. Restart Home Assistant.

## Programme recognition

Automatic recognition remains **provisional** until ≥3 labelled real traces exist per
programme. Synthetic test fixtures do not satisfy this gate. Unlabelled Auto runs are
archived as `unknown` and excluded until relabelled via `washercycle.relabel_last_cycle`.
