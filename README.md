# WasherCycle

Home Assistant custom integration for monitoring a Samsung WW75J54E0IW/SA washing machine using a SmartThings smart plug (Zigbee2MQTT) and door contact.

WasherCycle is the single authority for appliance-derived state: cycle detection, programme identification, progress/ETA, completion, and emptying detection. Notifications are handled by the included Home Assistant package.

## Features (v2)

- Automatic cycle recording — no manual start/mark-complete buttons
- Time-aligned programme matching with real-trace acceptance gate (≥3 runs per programme)
- Immediate completion events with async post-window archiving
- Door-authoritative emptying and rewash detection
- Shadow mode for safe rollout alongside legacy automations
- Diagnostics with accuracy metrics and trace replay

## Stable public contract

| Entity | Purpose |
|--------|---------|
| `sensor.washercycle_state` | idle, starting, running, finishing, needs_emptying, needs_rewash, unavailable |
| `sensor.washercycle_program` | Unknown, Quick Wash, Daily Wash, Bedding, Drum Clean |
| `sensor.washercycle_progress` | 0–100% |
| `sensor.washercycle_time_remaining` | Seconds |
| `sensor.washercycle_expected_completion` | Timezone-aware timestamp |
| `select.washercycle_next_program` | Calibration selector (Auto + four programmes) |
| `binary_sensor.washercycle_running` | Cycle active |
| `binary_sensor.washercycle_needs_emptying` | Load ready to unload |

## Installation

### HACS

1. Add this repository as a custom repository in HACS
2. Install **WasherCycle** integration
3. Restart Home Assistant
4. Add integration via **Settings → Devices & Services → Add Integration → WasherCycle**

### Manual

Copy `custom_components/washercycle` to your Home Assistant `custom_components` directory and restart.

## Configuration

Required:

- Power sensor (`sensor.laundry_washerplug_power`)
- Door contact (`binary_sensor.laundry_washerdoor_contact`)

Recommended:

- Energy sensor (`sensor.laundry_washerplug_energy`)

Optional:

- Movement sensor (`binary_sensor.laundry_washerdoor_moving`)
- Plug switch (diagnostics only; WasherCycle never turns the plug off)

Options:

- **Shadow mode** — suppress operational events during rollout (default on)
- **Rewash delay** — minutes before `needs_rewash` (default 120)
- **Advanced diagnostics** — enables hidden `force_empty` service

## Calibration workflow

1. Select a programme on `select.washercycle_next_program`
2. Start the washer normally
3. WasherCycle detects the start, records the cycle, and saves it after completion
4. Selector returns to Auto after archive finalisation
5. Repeat 2–3 times per programme for reliable auto-identification

## Rollout

See [docs/MIGRATION.md](docs/MIGRATION.md) for the v1→v2 migration and six-step rollout order.

## Trace fixtures

See [docs/FIXTURES.md](docs/FIXTURES.md) for synthetic vs real trace policy and export instructions.

## Development

```bash
./scripts/test.sh          # Run tests
ruff check custom_components tests
```

## License

MIT
