# ADR-0001: Architecture Import Boundaries and Ratchet Gate

## Status
Accepted (2026-02-22), Amended A1 (2026-02-22)

## Context
최근 12개월 변경 이력에서 `newsletter/`와 `web/`의 결합 지점이 반복적으로 변경되었고,
고빈도 모듈(`newsletter/chains.py`, `newsletter/cli.py`, `newsletter/tools.py`,
`newsletter/graph.py`, `newsletter/compose.py`, `web/app.py`)에 책임이 집중되어 있습니다.

현재 방향성(`web -> newsletter`, `newsletter -> web` 없음)은 관찰되지만,
CI에서 구조 규칙을 강제하지 않아 회귀 가능성이 존재합니다.

## Decision
다음 규칙을 CI에서 강제합니다.

1. `newsletter -> web` import 금지 (즉시 실패)
2. `web -> newsletter` import 금지 (즉시 실패, `newsletter_core.public`만 허용)
3. `newsletter_core.domain -> newsletter_core.infrastructure` import 금지
4. `newsletter_core.internal`은 `newsletter_core` 패키지 외부 import 금지
5. 모듈 cycle(SCC 크기 > 1) 금지

또한 도입 초기에는 `ratchet` 모드로 운영합니다.

- 기준 파일: `scripts/architecture/boundary_baseline.json`
- 정책: baseline 대비 신규/확대 위반만 차단
- 감소는 허용

## Consequences
- 장점: 대규모 이동 전 구조 drift를 차단하고, 점진 이행의 안전성을 확보합니다.
- 비용: 규칙 파일/기준선 관리가 필요하며, 신규 경계 추가 시 rules 업데이트가 필요합니다.

## Implementation
- 규칙 파일: `scripts/architecture/boundary_rules.yml`
- 경계 검사기: `scripts/architecture/check_import_boundaries.py`
- cycle 검사기: `scripts/architecture/check_import_cycles.py`
- 로컬 게이트: `make check`
- CI 게이트: `.github/workflows/main-ci.yml`

## Rollout
1. Ratchet 모드로 시작
2. legacy 경로 축소에 따라 baseline 감소 반영
3. legacy 제거 시 strict 모드 전환 검토

## Amendment A1 (2026-02-22)
- 배경: PR-5에서 `web` 런타임이 `newsletter_core.public` 경유로 전환됨.
- 변경: 기존 `web -> newsletter` 허용목록 규칙을 제거하고 전면 금지로 강화.
- 기대효과: 웹 경계에서 레거시 패키지 재유입을 CI 단계에서 즉시 차단.
