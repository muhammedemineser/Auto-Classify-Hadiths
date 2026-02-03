#!/usr/bin/env bash
set -euo pipefail

pytest -q tools/tafsir_gui/tests/unit
if [[ "${RUN_E2E:-0}" == "1" ]]; then
  pytest -q tools/tafsir_gui/tests/e2e
fi
