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

## Operational Safety Reinforcement
- sync/async/redis-fallback/thread-fallback 경로는 동일 응답 스키마와 동일 DB 상태전이 함수를 사용해야 합니다.
- 생성 요청은 idempotency key를 기준으로 중복 요청을 재사용해야 합니다.
- 이메일 발송 경로는 outbox/send_key 기반 중복 방지 정책을 반드시 적용해야 합니다.
- in-memory fallback 경로는 DB 상태전이를 분기별로 직접 구현하지 않고 공통 함수만 사용해야 합니다.
- 신규 동적 모듈 로딩(`importlib.util.spec_from_file_location`)은 원칙적으로 금지하며, 예외는 사유를 PR에 명시합니다.

## Additional Required Tests
- `pytest tests/contract/test_web_email_routes_contract.py -q`
- `pytest tests/unit_tests/test_config_import_side_effects.py -q`
- 중복 enqueue / 재시도 / 이메일 재발송 방지 시나리오 테스트를 포함합니다.
