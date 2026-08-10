# Trace Fixtures

## Synthetic vs real traces

- **Synthetic fixtures** in `tests/fixtures/` validate algorithm mechanics only.
- They do **not** prove reliable recognition of the Samsung WW75J54E0IW/SA washer.
- Automatic programme recognition remains provisional until **≥3 labelled real traces**
  exist per programme: Quick Wash, Daily Wash, Bedding, Drum Clean.

## Exporting real traces

```bash
python scripts/export_run.py --run-id <uuid> --output traces/daily_wash_run1.json
```

Redact household identifiers before committing. Real traces should be stored under:

```
tests/fixtures/real/<program_id>/run_N.json
```

## Replay and metrics

```bash
python scripts/replay_trace.py tests/fixtures/daily_wash/sample.json
```

Replay output includes programme prediction timeline, completion latency, ETA error,
and reporting gap statistics. Review metrics before tuning thresholds or disabling
shadow mode.

## Leave-one-out evaluation

With ≥3 real traces per programme, run:

```bash
pytest tests/test_loo_evaluation.py -v
```

Skip if real fixtures are not yet committed.
