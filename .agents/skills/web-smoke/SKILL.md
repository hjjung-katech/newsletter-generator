---
name: web-smoke
description: Validate Flask web runtime behavior for health and generation endpoints with lightweight end-to-end checks.
---

1. Start/target Flask web service.
2. Check `/health` and required dependency fields.
3. Trigger `/api/generate` with safe mock payload.
4. Poll `/api/status/<job_id>` until completion/failure threshold.
5. Report status transitions and payload schema conformance.
