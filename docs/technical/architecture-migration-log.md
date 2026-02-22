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
  - `.github/workflows/ci.yml`
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

### Compatibility policy
- Legacy compatibility shims retained for 2 release cycles.
- `newsletter.api` now emits `DeprecationWarning` and re-exports from `newsletter_core.public.generation`.

### Next checkpoints
- Switch deployment/runtime commands to `apps/*` wrappers as primary entrypoints.
- Move remaining worker/scheduler orchestration behind `newsletter_core.public` use-cases.
- Remove legacy shims after deprecation window.

### Verification snapshot (local)
- Environment bootstrap:
  - `.venv` created and dependencies installed from `requirements.txt` and `requirements-dev.txt`.
- Passed:
  - `python3 scripts/architecture/check_import_boundaries.py --mode ratchet`
  - `python3 scripts/architecture/check_import_cycles.py`
  - `.venv/bin/python run_ci_checks.py --quick`
  - `.venv/bin/python -m pytest tests/contract/test_generation_facade.py -q`
  - `.venv/bin/python -m pytest tests/test_web_api.py -q`
  - `.venv/bin/python -m pytest tests/unit_tests/test_schedule_time_sync.py -q`
  - `RUN_INTEGRATION_TESTS=1 GEMINI_API_KEY=dummy SERPER_API_KEY=dummy POSTMARK_SERVER_TOKEN=dummy .venv/bin/python -m pytest tests/integration/test_cli_integration.py -q`
  - `RUN_INTEGRATION_TESTS=1 GEMINI_API_KEY=dummy SERPER_API_KEY=dummy POSTMARK_SERVER_TOKEN=dummy .venv/bin/python -m pytest tests/integration/test_schedule_execution.py -q`
- Note:
  - without API keys, integration-marked suites are skipped by `tests/conftest.py`.
