#!/bin/bash
# Compatibility shim for legacy root script path.

set -euo pipefail

TARGET="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/devtools/newsletter-test.sh"

if [ ! -f "$TARGET" ]; then
  echo "[shim-error] Missing target script: $TARGET" >&2
  exit 2
fi

echo "[deprecated] newsletter-test.sh moved to scripts/devtools/newsletter-test.sh" >&2
exec "$TARGET" "$@"
