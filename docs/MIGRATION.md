# WasherCycle v1 → v2 Migration

## Overview

Version 2.0 refocuses WasherCycle on the Samsung WW75J54E0IW/SA with automatic cycle
recording, time-aligned matching, and notifications handled by the Home Assistant package.

## Rollout order

1. Install v2 in **shadow mode** (default on).
2. Collect and replay real traces; review diagnostics metrics.
3. Validate state, programme, ETA, completion, and door behaviour.
4. Install `examples/packages/washercycle_notifications.yaml`.
5. Remove legacy washer automations.
6. Disable shadow mode.

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

Stable contract entities unchanged:

- `sensor.washercycle_state`, `sensor.washercycle_program`, `sensor.washercycle_progress`
- `sensor.washercycle_time_remaining`, `sensor.washercycle_expected_completion`
- `binary_sensor.washercycle_running`, `binary_sensor.washercycle_needs_emptying`

## Storage migration

Storage automatically migrates from v1 to v2 on load:

- Removes `announcement_state`
- Flags manual-timing runs with `manual_timing` anomaly
- Rebuilds profile schema with `recognition_ready` gates

Back up `.storage/washercycle.storage_*` before upgrading.

## Rollback

1. Stop Home Assistant.
2. Restore v1 storage backup.
3. Reinstall WasherCycle 1.0.1 via HACS.
4. Restart Home Assistant.

## Programme recognition

Automatic recognition remains **provisional** until ≥3 labelled real traces exist per
programme. Synthetic test fixtures do not satisfy this gate.
