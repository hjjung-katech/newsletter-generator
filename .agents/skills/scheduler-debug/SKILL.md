---
name: scheduler-debug
description: Debug RRULE schedule execution, window handling, duplicate prevention, and Redis fallback behavior.
---

# Scheduler Debug

1. Inspect schedule state (`enabled`, `next_run`, `is_test`, `expires_at`).
2. Reproduce execution window behavior (regular 30m, test 10m).
3. Verify pre-update of `next_run` prevents duplicate execution.
4. Validate Redis queue path and synchronous fallback path.
5. Add/adjust focused tests for regressions.
