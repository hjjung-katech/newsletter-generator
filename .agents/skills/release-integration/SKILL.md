---
name: release-integration
description: Enforce release preflight and manifest-scoped changes for integration work.
---

1. Run release preflight checks.
2. Validate staged changes against the intended release manifest.
3. Execute mapped Makefile gates.
4. Report out-of-scope files or missing baseline requirements.
5. Return a clear pass/fail decision with remediation steps.
