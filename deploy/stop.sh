#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker/docker-compose.yml"
PROFILE="${1:-dev}"

echo "Stopping stack (profile=$PROFILE)..."
docker compose -f "$COMPOSE_FILE" --profile "$PROFILE" down
