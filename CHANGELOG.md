# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-08-12

### Fixed

- Cycle isolation: each new wash gets a fresh cycle record, trace, and energy baseline
- Energy accumulation uses source energy at cycle start (including tick-confirmed starts)
- Door-correlated completion no longer skips the needs-emptying state
- Completion archiving always runs through the post-window; no immediate-empty shortcut
- Unlabelled Auto runs archive as `unknown` and are excluded from profile learning
- Diagnostics no longer reference removed recorder/announcement internals
- Obsolete entity registry entries are removed automatically on setup

### Changed

- Storage schema v3: one-time reset of unreliable v2.0.4 learning data on upgrade
- `pending_program` resets to `auto` after each archived cycle
- Supported entity contract: 9 sensors + 2 binary sensors + 1 select (no buttons)
- `async_remove_entry` deletes per-entry storage on uninstall

### Removed

- `CycleRecord.announcement`, `immediately_emptied`, and `active_recording` storage
- Training/recording buttons and related translation strings
- Announcement/TTS options from strings (already absent from options flow)

## [2.0.4] - 2026-08-10

### Fixed

- Options flow no longer assigns read-only `config_entry` on current Home Assistant
  (fixes 500 / `AttributeError: property 'config_entry' has no setter`)

## [2.0.3] - 2026-08-10

### Fixed

- Register Home Assistant `Store` migration callback so v1 installations upgrade
  without `NotImplementedError` during `async_load()`
- Preserve calibration runs, active cycle, and pending programme selection during
  v1 → v2 storage migration

## [2.0.2] - 2026-08-10

### Fixed

- CI test workflow: pin compatible pytest/HA stack and use Python 3.12 only to avoid pip backtracking
- Ruff lint failures across integration and test code

### Removed

- Legacy v1 modules no longer used by v2 (`announcements`, `evidence`, `training`)

## [2.0.0] - 2026-08-10

### Changed

- Refocused integration on Samsung WW75J54E0IW/SA with automatic cycle recording
- Time-aligned programme matching with real-trace acceptance gate (≥3 runs per programme)
- Immediate completion events with async post-window archiving
- Timer-only internal tick; power samples from power entity only
- Simplified configuration: power + door required; energy recommended; plug switch optional
- Notifications moved to Home Assistant package; shadow mode suppresses operational events
- Storage schema v2 with migration from v1

### Removed

- Training buttons and manual start/mark-complete workflow
- In-integration TTS announcements and related options
- Non-contract diagnostic entities from default platforms

### Added

- `washercycle.relabel_last_cycle` developer service
- Accuracy metrics in diagnostics and replay output
- Synthetic and real trace fixture documentation (`docs/FIXTURES.md`)
- Comprehensive contract, sampling, idempotency, and migration tests

## [1.0.1] - 2026-07-31

### Fixed

- Correct `_attr_native_unit_of_measurement` typo that prevented sensor platform import

## [1.0.0] - 2026-07-31

### Added

- Initial WasherCycle integration for Samsung WW75J54E0IW/SA
