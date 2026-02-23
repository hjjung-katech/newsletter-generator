---
name: docs-and-config-consistency
description: Reconcile docs, env samples, and runtime config to a single source of truth. Use for config unification, import side-effect checks, and canonical env drift.
---

# Docs And Config Consistency

1. Scan runtime + docs drift:
   - `newsletter/centralized_settings.py`
   - `newsletter/config_manager.py`
   - `README.md`, `docs/`, `web/.env.example`
2. Enforce canonical env contract:
   - canonical: `POSTMARK_SERVER_TOKEN`, `EMAIL_SENDER`
   - alias-only: `POSTMARK_FROM_EMAIL`
3. Validate config unification rules:
   - no import-time `load_dotenv()` side effect
   - production-safe defaults (`test_mode=False`)
   - centralized validation path preserved
4. Run verification:
   - `pytest tests/unit_tests/test_config_import_side_effects.py -q`
   - `pytest tests/unit_tests/test_centralized_settings.py -q`
5. Output template:
   - changed files
   - command list
   - pass/fail evidence
   - unresolved drift items
