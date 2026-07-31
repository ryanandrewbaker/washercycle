#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements_test.txt
python3 -m pytest tests/ -v --tb=short "$@"
