# Web Instructions (override)

## High-risk rules
- Do not use subprocess-based newsletter generation in `web` runtime paths.
- Do not hardcode virtualenv interpreter paths (for example `.venv/Scripts/python.exe`).
- Use `newsletter_core.public.generation.generate_newsletter` for generation.
- Keep response schema stable across sync/async execution paths:
  - `status`, `html_content`, `title`, `generation_stats`, `input_params`, `error`

## Required tests for web scheduler/worker changes
- `pytest tests/test_web_api.py -q`
- `pytest tests/integration/test_schedule_execution.py -q`
- `pytest tests/unit_tests/test_schedule_time_sync.py -q`
