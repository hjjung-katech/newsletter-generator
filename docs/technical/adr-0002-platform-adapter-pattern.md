# ADR-0002: Platform Adapter Pattern

## Status
Accepted

## Context
Platform-specific branching (Windows UTF-8 setup, freeze detection, signal handling, venv paths) was duplicated inline across `web/` and `newsletter_core/` modules. This made it hard to add new platforms and caused `ctypes.windll` to be imported on non-Windows hosts.

## Decision
Introduce `newsletter_core/infrastructure/platform/` as the single location for all platform-specific logic. A `PlatformAdapter` Protocol (`_protocol.py`) defines the interface; `_windows.py` and `_unix.py` provide concrete implementations selected at runtime by `_resolver.py` using lazy imports. Supporting modules `_frozen.py`, `_signal.py`, and `_paths.py` consolidate previously duplicated inline helpers. The public API is exposed via `newsletter_core.public.platform`. Existing `web/` shims are retained as thin backward-compatible delegation layers only.

## Consequences
- Platform branches are isolated to `_windows.py` / `_unix.py`; app code stays platform-agnostic.
- `ctypes.windll` is never imported on Unix hosts (lazy resolver).
- Freeze detection and signal setup are deduplicated across the codebase.
- Backward compatibility is preserved via `web/platform_adapter.py`, `web/runtime_paths.py`, and `web/binary_compatibility.py` delegation layers.
- New platform-specific behavior must go in `_windows.py` / `_unix.py`, not inline in app code.
