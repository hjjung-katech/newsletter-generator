#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

git -C "$ROOT_DIR" config --local commit.template .github/COMMIT_TEMPLATE.txt

echo "Configured local commit template:"
echo "  .github/COMMIT_TEMPLATE.txt"
echo
echo "Branch naming template:"
echo "  codex/<kebab-case-topic>"
echo "Examples:"
echo "  codex/repo-hygiene-week3"
echo "  codex/fix-ci-process-guard"
