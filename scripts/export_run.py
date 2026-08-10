#!/usr/bin/env python3
"""Export a training run trace for fixture collection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export WasherCycle training run")
    parser.add_argument("--input", required=True, help="Path to storage JSON export")
    parser.add_argument("--run-id", required=True, help="Training run ID to export")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())
    runs = data.get("training_runs", [])
    run = next((r for r in runs if r.get("run_id") == args.run_id), None)
    if not run:
        raise SystemExit(f"Run {args.run_id} not found")

    export = {
        "program_id": run.get("program_id"),
        "synthetic": False,
        "run_id": run.get("run_id"),
        "events": [],
    }
    for sample in run.get("raw", {}).get("power", []):
        export["events"].append(
            {
                "timestamp": sample.get("t"),
                "kind": "power",
                "value": sample.get("w"),
            }
        )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(export, indent=2))
    print(f"Exported {len(export['events'])} power events to {out}")


if __name__ == "__main__":
    main()
