#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

SOURCE_FILE="backend/.env"
TARGET_FILE="config/backend.env"

if [ ! -f "$SOURCE_FILE" ]; then
  echo "source file not found: $SOURCE_FILE"
  exit 1
fi

mkdir -p config

if [ -f "$TARGET_FILE" ]; then
  TS="$(date +%Y%m%d_%H%M%S)"
  cp "$TARGET_FILE" "${TARGET_FILE}.bak.${TS}"
  echo "backup created: ${TARGET_FILE}.bak.${TS}"
fi

cp "$SOURCE_FILE" "$TARGET_FILE"
echo "migrated: $SOURCE_FILE -> $TARGET_FILE"
echo "next: start scripts now read config/backend.env by default."
