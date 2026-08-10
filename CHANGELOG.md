# Changelog

All notable changes to this project will be documented in this file.

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
