# Project Instructions (newsletter-generator)

## Non-negotiables
- Never commit secrets. Never print real API keys in logs, docs, or PR descriptions.
- Default to MOCK_MODE for local tests and smoke runs unless explicitly testing real APIs.
- Keep Flask + Postmark as the canonical runtime stack for web delivery.
- Keep FastAPI under `apps/experimental/` only (non-canonical runtime path).
- Treat `POSTMARK_SERVER_TOKEN` and `EMAIL_SENDER` as canonical env vars.
- Allow `POSTMARK_FROM_EMAIL` only as a read-only compatibility alias.
- Do not introduce `SENDGRID_API_KEY`, `FROM_EMAIL`, `POSTMARK_TOKEN`, or `POSTMARK_API_TOKEN` into active docs/samples.

## Required Gate After Code Changes
- Run: `make check-full`
- If full run is too expensive during iteration, run: `make check` first and then `make check-full` before completion.

## PR Size Policy
- Keep each PR within 300 LOC and 8 files whenever possible.
- For large refactors, lock contract tests first and split into sequential PRs.

## Repo Truth Sources
- CI gate: `run_ci_checks.py`
- Release preflight: `scripts/release_preflight.py`
- Manifest validator: `scripts/validate_release_manifest.py`
- Release manifests: `.release/manifests/*.txt`

## Required Report Format For Changes
- Short summary: what changed and why
- Exact commands executed
- Pass/fail evidence from checks/tests
- What was not run and why

## High-Risk Areas (extra caution)
- `web/app.py`, `web/tasks.py`, `web/schedule_runner.py`
- `newsletter/centralized_settings.py`, `newsletter/config_manager.py`
- Release gate scripts and Makefile targets
