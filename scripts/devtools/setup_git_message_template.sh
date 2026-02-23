#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

git -C "$ROOT_DIR" config --local commit.template .gitmessage.txt

echo "Configured local commit template:"
echo "  .gitmessage.txt"
echo
echo "Branch naming template:"
echo "  <type>/<scope>-<topic>"
echo "Examples:"
echo "  codex/workflow-template-standard"
echo "  fix/scheduler-duplicate-send"
