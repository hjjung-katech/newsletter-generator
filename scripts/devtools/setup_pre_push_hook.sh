#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SOURCE_HOOK="$ROOT_DIR/scripts/devtools/hooks/pre-push"
TARGET_HOOK="$ROOT_DIR/.git/hooks/pre-push"

if [ ! -f "$SOURCE_HOOK" ]; then
  echo "❌ Source hook not found: $SOURCE_HOOK"
  exit 1
fi

if [ -f "$TARGET_HOOK" ]; then
  BACKUP_HOOK="$ROOT_DIR/.git/hooks/pre-push.backup.$(date +%Y%m%d%H%M%S)"
  cp "$TARGET_HOOK" "$BACKUP_HOOK"
  echo "ℹ️ Existing pre-push hook backed up: $BACKUP_HOOK"
fi

cp "$SOURCE_HOOK" "$TARGET_HOOK"
chmod +x "$TARGET_HOOK"

echo "✅ Installed pre-push hook: $TARGET_HOOK"
echo "ℹ️ Hook source: $SOURCE_HOOK"
