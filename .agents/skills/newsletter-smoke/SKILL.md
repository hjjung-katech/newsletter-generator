---
name: newsletter-smoke
description: Run fast newsletter generation smoke checks in MOCK_MODE and validate expected HTML/output shape.
---

1. Export test-safe env defaults (`MOCK_MODE=true`, test API placeholders).
2. Run a minimal generation path through core code.
3. Validate output exists and includes expected HTML structure.
4. Return pass/fail with failing step and likely root cause.
