---
name: ci-gate
description: Run the local CI gate using run_ci_checks.py and report actionable failures. Use for lint/test readiness, pre-commit checks, CI parity checks, and PR hardening.
---

# CI Gate

1. Detect scope from staged changes by default.
2. Run `make check-full`.
3. If failures remain, summarize failing checks and minimal fixes required.
4. Re-run the same command and report final status.
5. Report commands, pass/fail evidence, and unresolved risks.
