# Project Instructions (newsletter-generator)

This file defines repository-specific constraints only.
Global execution behavior is in `~/.codex/AGENTS.md`.
If guidance conflicts, follow this file for this repository.
Instruction layout reference: `docs/dev/CODEX_INSTRUCTION_LAYOUT.md`.

## Non-negotiables
- Default to `MOCK_MODE` for local tests and smoke runs unless explicitly testing real APIs.
- Keep Flask + Postmark as the canonical web runtime stack.
- Keep FastAPI under `apps/experimental/` only (non-canonical runtime path).
- Canonical env vars: `POSTMARK_SERVER_TOKEN`, `EMAIL_SENDER`.
- Allow `POSTMARK_FROM_EMAIL` only as a read-only compatibility alias.
- Do not introduce `SENDGRID_API_KEY`, `FROM_EMAIL`, `POSTMARK_TOKEN`, or `POSTMARK_API_TOKEN` in active docs/samples.

## Web Runtime Guardrails
- Applies whenever touching `web/` runtime code, even if the Codex session starts at repo root.
- Do not use subprocess-based newsletter generation in web runtime paths.
- Use `newsletter_core.public.generation.generate_newsletter` for generation.
- Keep response schema stable across sync/async execution paths:
  - `status`, `html_content`, `title`, `generation_stats`, `input_params`, `error`
- Keep sync/async/redis-fallback/thread-fallback paths on common DB state-transition functions.
- Avoid new dynamic module loading (`importlib.util.spec_from_file_location`) in runtime code.
  If an exception is unavoidable, document the reason in the PR.

## Required Gates (Definition of Done)
- During iteration: `make check`
- Before completion: `make check-full`
- For ops-safety-sensitive changes (listed below), also run:
  - `pytest tests/test_web_api.py -q`
  - `pytest tests/integration/test_schedule_execution.py -q`
  - `pytest tests/unit_tests/test_schedule_time_sync.py -q`
  - `pytest tests/contract/test_web_email_routes_contract.py -q`
  - `pytest tests/unit_tests/test_config_import_side_effects.py -q`

Ops-safety-sensitive paths:
- `newsletter/centralized_settings.py`, `newsletter/config_manager.py`
- `web/app.py`, `web/tasks.py`, `web/schedule_runner.py`
- `web/routes_generation.py`, `web/routes_send_email.py`

## Ops-Safety Lock (Mandatory)
- Prioritize operational safety over boundary refactors until both are stable:
  - config unification around `newsletter/centralized_settings.py`
  - scheduler/worker idempotency + email dedupe via outbox/send_key
- Keep `newsletter/centralized_settings.py` as single source of truth for config.
- Keep `newsletter/config_manager.py` as a thin compatibility adapter.
- Do not allow import-time side effects (for example `load_dotenv()` on module import).
- Production defaults must remain production-safe (`test_mode=False` by default).
- Idempotency policy:
  - prefer `Idempotency-Key`; fallback to canonical payload-hash key
  - same logical request must reuse the same idempotency key/job
  - duplicate requests must return `202` with `deduplicated=true`
  - sync/async/fallback paths must share common DB state-transition functions

## Ops-Safety Reporting (Required When Applicable)
- For ops-safety-sensitive changes, include:
  - idempotency key generation and where it is applied
  - outbox/send_key duplicate-prevention behavior or verification result
  - whether import-time side effects were introduced, avoided, or removed
  - skipped tests and reasons

## Workflow Contract (RR/Branch/Commit/PR)
- Standard flow: RR -> Branch -> Commit -> PR -> Merge.
- RR template: `.github/ISSUE_TEMPLATE/review-request.yml`
- Branch naming: `<type>/<scope>-<topic>`
- Commit messages follow `.gitmessage.txt`.
- PR body must complete `.github/pull_request_template.md`.
- Keep RR and PR as 1:1 delivery units (`RR: #<n>` and `Delivery Unit ID` required).
- Do not reuse one RR (or Delivery Unit ID) across multiple open PRs.
- Keep each PR within about 300 LOC and 8 files when possible.
- For large refactors, lock contract tests first and split into sequential PRs.
- Default merge strategy is squash; exceptions require explicit evidence.

## Skill Routing (Prefer Skills for Repetitive Playbooks)
- Keep this file short; move repetitive procedures into `.agents/skills/*/SKILL.md`.
- Use these repo skills when relevant:
  - `ci-gate`: local CI/ops-safety gates and failure triage
  - `scheduler-debug`: RRULE/idempotency/duplicate-prevention debugging
  - `web-smoke`: Flask health + generation endpoint smoke checks
  - `docs-and-config-consistency`: docs/config SSOT consistency checks
  - `release-integration`: pre-release integration checks

## Repo Truth Sources
- CI gate: `run_ci_checks.py`
- Release preflight: `scripts/release_preflight.py`
- Manifest validator: `scripts/validate_release_manifest.py`
- Release manifests: `.release/manifests/*.txt`

## High-risk Areas (Extra Caution)
- `web/app.py`, `web/tasks.py`, `web/schedule_runner.py`
- `newsletter/centralized_settings.py`, `newsletter/config_manager.py`
- Release gate scripts and Makefile targets
