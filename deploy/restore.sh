#!/usr/bin/env sh
set -eu

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup_directory>" >&2
  exit 1
fi

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
SOURCE="$1"

if [ ! -d "$SOURCE/data" ]; then
  echo "Backup data folder not found: $SOURCE/data" >&2
  exit 1
fi

echo "Restoring data from $SOURCE/data to $ROOT/data"
rm -rf "$ROOT/data"
cp -R "$SOURCE/data" "$ROOT/data"
echo "Restore complete."
