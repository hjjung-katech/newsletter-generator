# Shim Deprecation Schedule (newsletter -> newsletter_core)

## Scope
- Legacy compatibility shims under `newsletter/` that re-export from `newsletter_core`.
- Primary shim entrypoint: `newsletter/api.py`.

## Policy
- Grace window: next 2 official release tags after introduction.
- Removal point: third official release tag after introduction.
- Introduction point: `2026-02-22` stack merge (`PR-0` ~ `PR-5`).

## Release-tag timeline
1. `N` (introduced): warnings enabled, behavior fully backward compatible.
2. `N+1`: keep shims, block new direct imports of deprecated paths and freeze the `newsletter/` Python surface.
3. `N+2`: keep shims, migration completion target for remaining consumers.
4. `N+3`: remove shim modules and deprecated import paths.

## Enforcement checklist
- CI boundary check keeps `web -> newsletter` forbidden.
- CI legacy surface guard keeps new Python modules from landing under `newsletter/`.
- Deprecated path usage tracked by grep:
  - `rg "newsletter\\.api|newsletter\\.(collect|summarize|compose|deliver)" -n`
- Before `N+3` cut:
  - no runtime consumer depends on shim path
  - contract/integration tests pass without shim-only imports

## Ownership
- Architecture policy owner: `CODEOWNERS` (`apps/**`, `newsletter_core/**`, `scripts/architecture/**`).
