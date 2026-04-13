# CLAUDE.md — Claude Code Workflow Contract

Repository-specific guidance for Claude Code working in this codebase.
See `AGENTS.md` for the Codex-specific workflow contract.

---

## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing tags.

---

## Architecture Boundaries

Import rules enforced by CI (see `docs/technical/adr-0001-architecture-boundaries.md`):

- `newsletter -> web` import is forbidden.
- `web -> newsletter` import is forbidden; use `newsletter_core.public` instead.
- `newsletter_core.domain -> newsletter_core.infrastructure` import is forbidden.
- New modules go under `newsletter_core/`, not `newsletter/`.

## Platform Adapter Architecture

All platform-specific code lives in `newsletter_core/infrastructure/platform/`.

**Getting the adapter:**
```python
from newsletter_core.public.platform import get_platform_adapter
adapter = get_platform_adapter()
```

**Module responsibilities:**

| Module | Purpose |
|---|---|
| `_protocol.py` | `PlatformAdapter` Protocol — defines the interface (`name`, `is_windows`, `configure_utf8_io`, `is_queue_supported`, `signal_names`, `venv_python_path`) |
| `_windows.py` | Windows implementation: UTF-8 locale/stream setup, SIGBREAK support, `Scripts/python.exe` path |
| `_unix.py` | Unix implementation: no-op UTF-8 setup, SIGINT+SIGTERM, `bin/python` path |
| `_resolver.py` | `get_platform_adapter()` factory with lazy imports (ctypes.windll never loads on Unix) |
| `_frozen.py` | `is_frozen()`, `is_frozen_any()`, `get_bundle_root()` — replaces duplicate inline freeze checks |
| `_signal.py` | `setup_signal_handlers()` — replaces platform branch in ShutdownManager |
| `_paths.py` | 5 path-resolution helpers — replaces inline logic in `web/runtime_paths.py` |

**Rule:** New platform-specific branching goes in `_windows.py` / `_unix.py`, not inline in app code.

Thin backward-compatible delegation layers exist at `web/platform_adapter.py`,
`web/runtime_paths.py`, and `web/binary_compatibility.py` — do not add logic there.

## Workflow Contract (RR → Branch → Commit → PR → Merge)

Standard flow for all implementation work:

1. **RR (Review Request)**: Create issue using `.github/ISSUE_TEMPLATE/review-request.yml`
   - Include: Goal, Delivery Unit ID (`DU-YYYYMMDD-<topic>`), Lifecycle Target, Scope, Risk
   - Must have `review-request` label (template adds it automatically)
2. **Branch**: Create from `main` with naming `<type>/<scope>-<topic>`
   - Allowed types: `feat|fix|chore|docs|refactor|release|codex`
   - CI regex: `^(feat|fix|chore|docs|refactor|release|codex)\/[a-z0-9._-]+$`
3. **Commit**: Follow `.gitmessage.txt` format
   - First line: `<type>(<scope>): <summary>` (72 chars max, CI-enforced)
   - Body: Why / What changed / Validation / Risk-Rollback
   - Commit count per PR: 1–6 (exempt labels: `docs-only`, `trivial`, `hotfix`)
4. **PR**: Complete `.github/pull_request_template.md` — all sections required by CI
5. **Merge**: Squash merge (default). After merge, verify RR close status

Rules:
- RR:PR = 1:1 — do not reuse one RR across multiple open PRs
- Never push directly to `main` — always use feature branches and PRs

## CI Gates

- During iteration: `make check`
- Before completion: `make check-full`
- Ops-safety-sensitive changes require additional tests:
  - `pytest tests/test_web_api.py -q`
  - `pytest tests/integration/test_schedule_execution.py -q`
  - `pytest tests/unit_tests/test_schedule_time_sync.py -q`
  - `pytest tests/contract/test_web_email_routes_contract.py -q`
  - `pytest tests/unit_tests/test_config_import_side_effects.py -q`

Ops-safety-sensitive paths:
- `newsletter/centralized_settings.py`, `newsletter/config_manager.py`
- `web/app.py`, `web/tasks.py`, `web/schedule_runner.py`
- `web/routes_generation.py`, `web/routes_send_email.py`

## Web Runtime Guardrails

- Do not use subprocess-based newsletter generation in web runtime paths.
- Use `newsletter_core.public.generation.generate_newsletter` for generation.
- Keep Flask + Postmark as the canonical web runtime stack.
- Keep FastAPI under `apps/experimental/` only.
- Avoid new dynamic module loading (`importlib.util.spec_from_file_location`) in runtime code.
- Keep response schema stable: `status`, `html_content`, `title`, `generation_stats`, `input_params`, `error`.

## Ops-Safety Lock

- Keep `newsletter/centralized_settings.py` as single source of truth for config.
- Keep `newsletter/config_manager.py` as a thin compatibility adapter.
- Do not allow import-time side effects (e.g., `load_dotenv()` on module import).
- Production defaults must remain production-safe (`test_mode=False` by default).
- Idempotency: prefer `Idempotency-Key`; fallback to canonical payload-hash key.
- Duplicate requests must return `202` with `deduplicated=true`.

## PR Convention

- Keep each PR within ~300 LOC and ~8 files.
- PR body must complete `.github/pull_request_template.md`.
- For large refactors, lock contract tests first and split into sequential PRs.

CI-required PR sections (policy-check enforced):
1. `## Summary (what / why)`
2. `## Scope`
3. `## Delivery Unit` — must include:
   - `RR: #<number>` (valid issue with `review-request` label)
   - `Delivery Unit ID:` (non-empty, e.g., `DU-20260413-topic`)
   - `Merge Boundary:` (non-empty)
   - `Rollback Boundary:` (non-empty)
4. `## Test & Evidence`
5. `## Risk & Rollback`
6. `## Ops-Safety Addendum (if touching protected paths)`
7. `## Not Run (with reason)`

## High-risk Areas (Extra Caution)

- `web/app.py`, `web/tasks.py`, `web/schedule_runner.py`
- `newsletter/centralized_settings.py`, `newsletter/config_manager.py`
- Release gate scripts and Makefile targets

## Key Docs

- Architecture: `docs/ARCHITECTURE.md`
- ADR index: `docs/technical/`
- Dev guide: `docs/dev/DEVELOPMENT_GUIDE.md`
- Local setup: `docs/setup/LOCAL_SETUP.md`
