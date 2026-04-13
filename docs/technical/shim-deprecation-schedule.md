# Shim Deprecation Schedule (newsletter -> newsletter_core)

## Scope
- Legacy compatibility shims under `newsletter/` that re-export from `newsletter_core`.
- Primary shim entrypoint: `newsletter/api.py`.

## Policy

### Version basis (updated 2026-04-13)
The removal schedule counts **CHANGELOG versions**, not git tags.
Git tags were not cut for the early 0.7.x releases, so the schedule is anchored
to documented CHANGELOG entries instead.

| Label | CHANGELOG version | Date | Status |
|---|---|---|---|
| N (introduced) | 0.7.0 | 2026-02-22 | complete |
| N+1 | 0.8.0 | 2026-02-23 | complete |
| N+2 | 0.9.0 | TBD | upcoming — shim consumer migration target |
| N+3 | 1.0.0 | TBD | **shim removal cut** |

### Release-tag timeline (original)
1. `N` (introduced): warnings enabled, behavior fully backward compatible.
2. `N+1`: keep shims, block new direct imports of deprecated paths and freeze the `newsletter/` Python surface.
3. `N+2`: keep shims, migration completion target for remaining consumers.
4. `N+3`: remove shim modules and deprecated import paths.

## Removal Progress

### Step 1 — Completed (PR #404, commit 91ff2de, 2026-04-13)

**Deleted files (zero live-import, pure shims):**
- `newsletter/collect.py` — 3-line wildcard re-export to `newsletter_core.application.generation.collect`
- `newsletter/summarize.py` — 3-line wildcard re-export to `newsletter_core.application.generation.summarize`
- `newsletter/main.py` — deprecated FastAPI entrypoint (DeprecationWarning at import)

**Associated cleanup:**
- `scripts/devtools/pyinstaller_hooks/hook-newsletter.py` — removed 3 module strings
- `web/binary_compatibility.py` — removed `newsletter.collect` module check string
- `newsletter/cli.py` — migrated `from . import collect` to `newsletter_core.application.generation`; removed unused `from . import summarize`
- `newsletter/cli_test.py` — migrated `from . import collect` to `newsletter_core.application.generation`

### Step 2 — Target: N+2 (0.9.0)

Files with active consumers that require migration before removal:

| File | Consumer | Replacement path |
|---|---|---|
| `newsletter/api.py` | `tests/contract/test_generation_facade.py` (intentional deprecation test) | Delete test with shim |
| `newsletter/compose.py` | `tests/unit_tests/test_compose_contract_lock.py` (contract lock test) | Delete test with shim |
| `newsletter/deliver.py` | `tests/api_tests/test_email_integration.py:35` (integration test) | `newsletter_core.application.generation.deliver` |

### Step 3 — Target: N+3 (1.0.0)

Files requiring production-code migration before removal:

| File | Consumer(s) | Migration effort |
|---|---|---|
| `web/platform_adapter.py` | `web/app.py:77` + 1 unit test | Low — swap to `newsletter_core.public.platform` |
| `newsletter/config.py` | `newsletter_core` internal imports in collect/summarize/deliver modules (3 files) | Medium — update newsletter_core internals |
| `newsletter/compat_env.py` | migration utility; depends on `config.py` being stable | Blocked by config.py migration |
| `newsletter/settings.py` | `LegacySettings` wrapper; depends on `centralized_settings` | Blocked by config.py migration |
| `web/runtime_paths.py` | `web/app.py:40`, `web/init_database.py`, `web/schedule_runner.py`, `web/tasks.py`, `web/newsletter_clients.py` (fallback) | High — ops-safety paths; requires separate PR |

### Long-term roadmap (not on N+3 schedule)

These are **maintenance-mode hotspots**, not pure shims. They contain
original orchestration logic and require a separate migration plan:

| File | Role | Extracted to |
|---|---|---|
| `newsletter/llm_factory.py` | Provider/fallback/runtime config shell | `newsletter_core/application/llm_factory*`, `infrastructure/llm_factory_runtime.py` |
| `newsletter/graph.py` | Legacy LangGraph orchestration shell | `newsletter_core/application/graph_workflow*`, `graph_node_helpers*`, `graph_composition*` |
| `newsletter/tools.py` | `@tool`-decorated search/delivery helpers | `newsletter_core/application/tools_search_flow*`, `tools_support*`, `infrastructure/tools_search_runtime*` |

## Enforcement checklist
- CI boundary check keeps `web -> newsletter` forbidden.
- CI legacy surface guard keeps new Python modules from landing under `newsletter/`.
- Deprecated path usage tracked by grep:
  - `rg "newsletter\.api|newsletter\.(collect|summarize|compose|deliver)" -n`
  - **Also check relative imports:** `rg "from \. import (collect|summarize|compose|deliver|main)" -n`

## Analysis notes

### Relative import blind spot (discovered 2026-04-13)
Searching only for absolute import patterns (`from newsletter.X import` / `import newsletter.X`)
misses relative imports within the same package (`from . import X`).
Before removing any shim, run **both** searches:
1. Absolute: `rg "from newsletter\.X import|import newsletter\.X" -n`
2. Relative: `rg "from \. import X" -n` (within the `newsletter/` package)

This was discovered during Step 1 — `newsletter/cli.py` and `newsletter/cli_test.py`
used `from . import collect` and `from . import summarize`, which the initial grep missed.

## Ownership
- Architecture policy owner: `CODEOWNERS` (`apps/**`, `newsletter_core/**`, `scripts/architecture/**`).
