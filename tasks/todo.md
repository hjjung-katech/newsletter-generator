# Tasks

## Prompt C — generation contract 테스트
- [ ] tests/contract/test_generation_routes_contract.py 신규 작성
- 대상 경로 4개:
    - POST /generate → 202 (first call)
    - POST /generate → 202 + dedup flag (duplicate)
    - POST /generate → 400 (missing required field)
    - POST /schedule/<id>/run → 202 (immediate execution)
- 제약: 신규 파일만, 소스 코드 및 기존 테스트 파일 수정 없음
- 패턴 참조: tests/contract/test_web_email_routes_contract.py
