# WasherCycle

Home Assistant custom integration for monitoring a Samsung WW75J54E0IW/SA washing machine using smart-plug power, door, and movement sensors.

WasherCycle learns your machine's real behaviour through manually recorded training runs and provides fast, explainable cycle detection, program recognition, progress/ETA, and configurable announcements.

## Features

- Training-first program profiles (Quick Wash, Daily Wash, Bedding, Drum Clean)
- Fast completion detection with explainable evidence scoring
- Door-open race handling
- Shadow mode for safe rollout alongside legacy automations
- Restart recovery
- Diagnostics and trace replay
- Event-driven mobile notifications (example package included)

## Installation

### HACS

1. Add this repository as a custom repository in HACS
2. Install **WasherCycle** integration
3. Restart Home Assistant
4. Add integration via **Settings → Devices & Services → Add Integration → WasherCycle**

### Manual

Copy `custom_components/washercycle` to your Home Assistant `custom_components` directory and restart.

## Configuration

The setup flow preselects known entity IDs:

- `sensor.laundry_washerplug_power`
- `sensor.laundry_washerplug_energy`
- `switch.laundry_washerplug`
- `binary_sensor.laundry_washerdoor_contact`
- `binary_sensor.laundry_washerdoor_moving`

Optional: temperature, link quality, and battery sensors.

## Training Workflow

1. Select training program on `select.washercycle_training_program_select`
2. Press **Start recording**
3. Start the washing machine
4. When you hear the Samsung completion chirp, press **Mark complete**
5. The run is saved and the program profile is rebuilt

Record at least 3 runs per program for automatic recognition, 5+ for robust end-signature modelling.

## Shadow Mode Rollout

Shadow mode is **enabled by default**. WasherCycle detects cycles and builds profiles without spoken announcements.

### Migration stages

1. **Stage 1:** Install WasherCycle (shadow mode). Keep legacy automations and `ha_washdata`.
2. **Stage 2:** Enable WasherCycle entities. Optionally enable `legacy_status_mirror` in options.
3. **Stage 2b:** Remove `ha_washdata`. Rename device to "Washing Machine" for canonical entity IDs.
4. **Stage 3:** Enable announcements. Install `examples/packages/washercycle_notifications.yaml`.
5. **Stage 4:** Disable legacy automations. Update dashboards.

## Entity naming

During shadow/coexistence with `ha_washdata`, entities use the `washercycle_*` prefix. After cutover, rename the device to claim `washing_machine_*` entity IDs.

## Troubleshooting

- Check **Settings → Devices & Services → WasherCycle → Diagnostics** for evidence scores and profile status
- Use `scripts/replay_trace.py` to replay exported training runs
- Power reporting cadence affects completion latency — check diagnostics for sensor gaps

## Development

On macOS, `pip` and `pytest` are often not on your PATH. Use `python3 -m …` instead:

```bash
python3 -m pip install -r requirements_test.txt
python3 -m pytest tests/ -v
python3 -m ruff check custom_components tests
```

Or run the helper script:

```bash
chmod +x scripts/test.sh   # once
./scripts/test.sh
```

For Home Assistant integration-test tooling (CI / Python 3.11+):

```bash
python3 -m pip install -r requirements_test_ha.txt
```

## License

MIT
