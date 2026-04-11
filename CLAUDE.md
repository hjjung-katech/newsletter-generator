# CLAUDE.md — Developer Guidance

Repository-specific guidance for AI coding assistants working in this codebase.
See `AGENTS.md` for the full workflow contract (RR/branch/commit/PR rules).

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

## Architecture Boundaries

Import rules enforced by CI (see `docs/technical/adr-0001-architecture-boundaries.md`):

- `newsletter -> web` import is forbidden.
- `web -> newsletter` import is forbidden; use `newsletter_core.public` instead.
- `newsletter_core.domain -> newsletter_core.infrastructure` import is forbidden.
- New modules go under `newsletter_core/`, not `newsletter/`.

## Key Docs

- Architecture: `docs/ARCHITECTURE.md`
- ADR index: `docs/technical/`
- Dev guide: `docs/dev/DEVELOPMENT_GUIDE.md`
- Local setup: `docs/setup/LOCAL_SETUP.md`
