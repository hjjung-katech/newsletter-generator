---
name: ci-gate
description: Run local CI/ops-safety gates and report actionable failures. Use for lint/test readiness, CI parity, and reliability lock checks.
---

# CI Gate

1. Detect scope from staged changes by default.
2. Run `make check-full`.
3. If ops-safety files changed, also run:
   - `pytest tests/test_web_api.py -q`
   - `pytest tests/integration/test_schedule_execution.py -q`
   - `pytest tests/unit_tests/test_schedule_time_sync.py -q`
4. If failures remain, summarize failing checks and minimal fixes required.
5. Re-run changed checks and report final status.
6. Report commands, pass/fail evidence, unresolved risks, and skipped checks.
