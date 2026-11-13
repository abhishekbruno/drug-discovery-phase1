#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export VINA_EXECUTABLE="$PWD/tools/vina"
exec .venv/bin/dockpipe ui
