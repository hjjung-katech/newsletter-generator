# Web Instructions (newsletter-generator/web)

This file adds web-runtime detail to the repository root `AGENTS.md`.
The root file still defines must-follow web guardrails for root-level sessions.
If guidance conflicts, follow this file while working under `web/`.

## Runtime Constraints
- Do not use subprocess-based newsletter generation in web runtime paths.
- Do not hardcode virtualenv interpreter paths (for example `.venv/Scripts/python.exe`).
- Use `newsletter_core.public.generation.generate_newsletter` for generation.
- Keep response schema stable across sync/async execution paths:
  - `status`, `html_content`, `title`, `generation_stats`, `input_params`, `error`
- Keep sync/async/redis-fallback/thread-fallback paths on common DB state-transition functions.
- Enforce idempotency reuse and outbox/send_key email dedupe on all web execution paths.
- Avoid new dynamic module loading (`importlib.util.spec_from_file_location`) in runtime code.
  If an exception is unavoidable, document the reason in the PR.

## Web Verification Additions
- Run root-level required gates first.
- When changing scheduler/worker/dedupe behavior, include scenario coverage for:
  - duplicate enqueue
  - retry safety
  - email resend prevention
