---
name: release-integration
description: Enforce release preflight, manifest scope, and ops-safety release reporting.
---

# Release Integration

1. Run release preflight checks.
2. Validate staged changes against the intended release manifest.
3. Execute mapped Makefile gates (`make check`, `make check-full`).
4. Generate ops-safety report:
   - idempotency coverage
   - outbox duplicate-prevention coverage
   - import side-effect checks
   - skipped tests with reasons
5. Report out-of-scope files or missing baseline requirements.
6. Return a clear pass/fail decision with remediation steps.
