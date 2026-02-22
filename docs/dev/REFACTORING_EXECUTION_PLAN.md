# Refactoring Execution Plan (Phase 5)

대상 대형 파일을 충돌 없이 분해하기 위한 실행 규칙입니다.

## Scope

- `web/app.py`
- `newsletter/cli.py`
- `newsletter/chains.py`

## Rules

1. 한 PR당 변경량은 300 LOC, 8 files 이내를 목표로 한다.
2. 계약(Contract) 테스트를 먼저 고정한 뒤 리팩터를 진행한다.
3. 각 PR은 독립적으로 `make check-full`을 통과해야 한다.
4. 아키텍처 경계(`scripts/architecture/*`)를 깨면 즉시 롤백한다.

## Suggested Slice Order

1. `web/app.py`
- 라우트 등록과 비즈니스 로직을 분리
- `web/routes/*`, `web/services/*` 단위로 점진 이동

2. `newsletter/cli.py`
- 커맨드 그룹별 모듈 분리 (`run`, `suggest`, `email`, `admin`)
- 엔트리 포인트는 파라미터 파싱/디스패치만 유지

3. `newsletter/chains.py`
- provider adapter, prompt builder, retry policy 분리
- 네트워크 호출 경계와 순수 함수 경계를 명확히 분리

## Definition of Done per Slice

- 기능 회귀 없음 (관련 unit/integration 통과)
- `make check-full` 통과
- 변경 이유/리스크/롤백 절차를 PR에 기록
