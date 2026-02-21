---
name: docs-and-config-consistency
description: Reconcile docs, env samples, and runtime config to a single source of truth. Use when email provider/env names/framework/runtime docs drift apart.
---

1. Scan README, setup docs, env examples, and runtime code for config drift.
2. Enforce canonical env contract:
   - `POSTMARK_SERVER_TOKEN`, `EMAIL_SENDER`
   - `POSTMARK_FROM_EMAIL` compatibility-only alias
3. Remove deprecated SendGrid/Postmark legacy names from active docs and samples.
4. Verify references and command examples still work.
5. Report a source-of-truth matrix: env var -> code usage -> doc locations.
