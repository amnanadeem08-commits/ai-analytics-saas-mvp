#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker/docker-compose.yml"
PROFILE="${1:-dev}"

echo "Validating environment..."
python - <<'PY'
from backend.config.config_loader import load_and_validate
_, validation = load_and_validate()
if not validation["valid"]:
    print("Configuration issues (non-fatal in dev):", validation["issues"])
print("Profile:", validation["profile"])
PY

echo "Starting stack (profile=$PROFILE)..."
docker compose -f "$COMPOSE_FILE" --profile "$PROFILE" up -d --build

echo "Waiting for backend readiness..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/api/v1/ready >/dev/null 2>&1; then
    echo "Backend is ready."
    exit 0
  fi
  sleep 2
done

echo "Backend did not become ready in time." >&2
exit 1
