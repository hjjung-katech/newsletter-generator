---
name: scheduler-debug
description: Debug RRULE schedule execution, idempotency, duplicate prevention, and Redis/thread/sync fallback consistency.
---

# Scheduler Debug

1. Inspect schedule state (`enabled`, `next_run`, `is_test`, `expires_at`).
2. Reproduce execution window behavior (regular 30m, test 10m).
3. Verify pre-update of `next_run` prevents duplicate execution.
4. Verify deterministic schedule key policy:
   - key source: `schedule_id + intended_run_at`
   - same logical run => same job identity
5. Validate Redis queue path and synchronous fallback path call the same task/state flow.
6. Run required tests:
   - `pytest tests/integration/test_schedule_execution.py -q`
   - `pytest tests/unit_tests/test_schedule_time_sync.py -q`
7. Report template:
   - scenario matrix (redis / thread-fallback / sync-fallback)
   - duplicate-execution evidence
   - unresolved risks
