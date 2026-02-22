# Architecture Migration Log

## 2026-02-22

### Completed
- Added architecture guardrails:
  - `scripts/architecture/check_import_boundaries.py`
  - `scripts/architecture/check_import_cycles.py`
  - `scripts/architecture/boundary_rules.yml`
  - `scripts/architecture/boundary_baseline.json`
- Wired guardrails into:
  - `run_ci_checks.py`
  - `.github/workflows/main-ci.yml`
  - `Makefile` (`architecture-check`, `architecture-baseline`)
- Introduced runtime/package skeleton:
  - `apps/cli`, `apps/web`, `apps/worker`, `apps/scheduler`
  - `packages/newsletter_core/src/newsletter_core/{public,application,domain,infrastructure,internal}`
- Migrated first generation slice to new location:
  - `collect.py`, `summarize.py`, `compose.py`, `deliver.py`
  - legacy shims left under `newsletter/`
- Added public facade:
  - `newsletter_core.public.generation`
  - `newsletter_core.public.settings`
  - `newsletter_core.public.lifecycle`
- Switched CLI runtime path to consume `newsletter_core.public.generation`.
- Added contract coverage:
  - `tests/contract/test_generation_facade.py`
  - updated `tests/integration/test_cli_integration.py`

### Merged PR stack (remote)
- PR-0: `#40` merged at `2026-02-22T04:50:59Z`
- PR-1: `#41` merged at `2026-02-22T04:51:33Z`
- PR-2: `#42` merged at `2026-02-22T04:51:48Z`
- PR-3: `#43` merged at `2026-02-22T04:52:02Z`
- PR-4: `#44` merged at `2026-02-22T04:52:12Z`
- PR-5: `#45` merged at `2026-02-22T04:53:09Z`
- Aggregate stack PR: `#46` merged at `2026-02-22T04:53:10Z`

### Main CI confirmation (post-merge)
- Final merge commit CI set completed with `success`:
  - Main CI Pipeline: run `22270734622`
  - Deployment Pipeline: run `22270734616`

### Post-merge hardening (started)
- `web -> newsletter` architecture rule tightened from allowlist to full forbid.
- `web` runtime guidance updated to use `newsletter_core.public.generation`.
- Legacy shim deprecation schedule documented in:
  - `docs/technical/shim-deprecation-schedule.md`

### Compatibility policy
- Legacy compatibility shims retained for 2 release cycles.
- `newsletter.api` now emits `DeprecationWarning` and re-exports from `newsletter_core.public.generation`.

### Next checkpoints
- Switch deployment/runtime commands to `apps/*` wrappers as primary entrypoints.
- Track and enforce shim removal milestones by release tags.
- Remove legacy shims at the third release tag after introduction.

### Verification snapshot (local)
- Environment bootstrap:
  - `.venv` created and dependencies installed from `requirements.txt` and `requirements-dev.txt`.
- Passed:
  - `python3 scripts/architecture/check_import_boundaries.py --mode ratchet`
  - `python3 scripts/architecture/check_import_cycles.py`
  - `make check`
  - `.venv/bin/python -m pytest tests/contract/test_generation_facade.py -q`
  - `.venv/bin/python -m pytest tests/test_web_api.py -q`
  - `.venv/bin/python -m pytest tests/unit_tests/test_schedule_time_sync.py -q`
  - `RUN_INTEGRATION_TESTS=1 GEMINI_API_KEY=dummy SERPER_API_KEY=dummy POSTMARK_SERVER_TOKEN=dummy .venv/bin/python -m pytest tests/integration/test_cli_integration.py -q`
  - `RUN_INTEGRATION_TESTS=1 GEMINI_API_KEY=dummy SERPER_API_KEY=dummy POSTMARK_SERVER_TOKEN=dummy .venv/bin/python -m pytest tests/integration/test_schedule_execution.py -q`
- Note:
  - without API keys, integration-marked suites are skipped by `tests/conftest.py`.
