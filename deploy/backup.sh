#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${1:-$ROOT/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="$BACKUP_DIR/backup_$STAMP"

mkdir -p "$TARGET"

echo "Backing up data directory..."
if [ -d "$ROOT/data" ]; then
  cp -R "$ROOT/data" "$TARGET/data"
fi

echo "Backing up docker volumes metadata..."
docker compose -f "$ROOT/docker/docker-compose.yml" ps > "$TARGET/docker_ps.txt" 2>/dev/null || true

echo "Backup written to $TARGET"
