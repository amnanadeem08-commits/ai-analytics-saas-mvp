#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"

"$ROOT/deploy/stop.sh" "$@"
"$ROOT/deploy/start.sh" "$@"
