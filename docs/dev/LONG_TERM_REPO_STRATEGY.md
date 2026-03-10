# Long-term Repo Strategy & Operating Playbook

이 문서는 현재 저장소 상태를 기준으로 리포 구조/운영 우선순위를 정렬하는 장기 정본(SSOT)입니다.
새로운 지원 정책이나 제품 비전을 정의하지 않고, 이미 운영 중인 계약을 현재 현실에 맞게 고정합니다.

- 기준일: 2026-03-10
- 적용 범위: repo structure, docs truthfulness, legacy surface reduction, ops observability
- 선행 정본:
  - `docs/reference/support-policy.md`
  - `docs/technical/adr-0001-architecture-boundaries.md`
  - `docs/dev/CI_CD_GUIDE.md`
  - `docs/dev/REPO_HYGIENE_POLICY.md`
  - `docs/README.md`

## 1) 운영 계약 (Current Operating Contract)

이 문서는 아래 계약을 다시 정의하지 않습니다. 다음 90일 작업은 모두 이 계약 안에서 수행합니다.

1. 지원/플랫폼/entrypoint 계약
- 정본: `docs/reference/support-policy.md`
- contributor-facing canonical entrypoint는 `python -m scripts.devtools.dev_entrypoint` 입니다.
- Flask + Postmark web runtime, Linux server packaging truth, Windows desktop exception 정책은 그대로 유지합니다.

2. 아키텍처 경계 계약
- 정본: `docs/technical/adr-0001-architecture-boundaries.md`
- 신규 기능은 `newsletter_core/` 아래에 추가합니다.
- `newsletter/` 는 호환 surface와 단계적 축소 대상입니다.
- `web -> newsletter` 직접 결합은 금지되며, `newsletter_core.public` 경유만 허용합니다.

3. CI / contributor workflow 계약
- 정본: `docs/dev/CI_CD_GUIDE.md`
- 로컬/CI 검증 truth는 `check`, `check --full`, docs checks, repo hygiene gate, ops-safety suites 조합입니다.
- Makefile은 유지하되 thin wrapper로 취급합니다.

4. repo hygiene 계약
- 정본: `docs/dev/REPO_HYGIENE_POLICY.md`
- repo hygiene hard gate, docs hub, strict audit 운영은 이미 활성 상태입니다.
- 현재 리포는 더 이상 "루트 정리 초기 단계"로 취급하지 않습니다.

## 2) 현재 상태 요약

### 현재 리포 상태

- tracked root 엔트리는 2026-03-10 로컬 인벤토리 기준 30개입니다.
- 루트 실행 스크립트 분산 문제는 대부분 정리되었고, repo hygiene hard gate가 이를 유지합니다.
- docs hub, support policy, ADR, CI guide가 이미 active 정본으로 운영 중입니다.
- 현재 제품 표면은 실질적으로 Flask web 운영 표면 중심이며, CLI/scheduler/automation이 이를 보조합니다.
- 남아 있는 구조 부채의 중심은 root clutter가 아니라 legacy runtime hotspot 입니다.

### 현재 위험이 집중된 hotspot

다음 파일들은 기능이 넓게 얽혀 있고, 축소 대상이지 확장 대상이 아닙니다.

| Path | Baseline LOC (2026-03-10) | 현재 의미 |
|---|---:|---|
| `web/routes_generation.py` | 1084 | generation web orchestration hotspot |
| `newsletter/tools.py` | 926 | legacy tool / source / save helper hotspot |
| `newsletter/llm_factory.py` | 848 | provider / fallback / runtime config hotspot |
| `newsletter/graph.py` | 705 | legacy orchestration hotspot |
| `web/static/js/app.js` | 2270 | single-file web operator UI hotspot |

추가 baseline:

- `newsletter/` Python 파일 수: 50
- `newsletter/` Python LOC: 12511
- `newsletter_core/` Python 파일 수: 20
- `newsletter_core/` Python LOC: 2310

## 3) 이미 달성된 항목

다음 항목은 더 이상 "앞으로 할 구조 정리"가 아니라 현재 운영 상태로 간주합니다.

- root cleanup 1차 목표 달성
  - tracked root 엔트리 수가 장기 전략 초기 목표치(30 이하)에 도달했습니다.
- repo hygiene hard gate 운영
  - strict audit와 artifact 업로드가 CI에 이미 연결돼 있습니다.
- docs hub / canonical docs 운영
  - `docs/README.md` 중심 정본 체계가 활성화돼 있습니다.
- architecture guardrail 운영
  - ADR, import boundary ratchet, legacy surface manifest가 활성 상태입니다.
- canonical developer entrypoint 정규화
  - contributor-facing run/check flow는 `python -m scripts.devtools.dev_entrypoint ...` 로 정리되었습니다.

이 문서의 다음 우선순위는 root cleanup 재개가 아니라, 이 상태를 유지하면서 legacy surface를 줄이는 것입니다.

## 4) 다음 90일 우선순위

### A. Legacy Surface Reduction

운영 계약:
- 신규 기능은 `newsletter_core/` 에만 누적합니다.
- `newsletter/` 와 hotspot `web/` 파일은 축소 대상입니다.
- protected path 변경은 기존 ops-safety contract suites를 먼저 고정한 뒤 진행합니다.

작업 단위:
1. `web/routes_generation.py` 를 request validation, job resolution, response shaping, route binding 계층으로 작은 배치로 분리합니다.
2. `newsletter/tools.py`, `newsletter/llm_factory.py`, `newsletter/graph.py` 의 pure logic를 `newsletter_core/` 또는 더 얇은 legacy wrapper로 점진 이동합니다.
3. `web/static/js/app.js` 는 preset/history/approval/source-policy/schedule 흐름 단위로 모듈 분할 후보를 문서화하고, 계약 테스트가 있는 경계부터 나눕니다.
4. extraction 전에 contract / ops-safety 테스트를 잠그고, behavior-preserving 배치만 merge 합니다.

완료 기준:
- `newsletter/` Python 파일 수와 LOC가 baseline 대비 감소합니다.
- hotspot LOC가 baseline 대비 감소합니다.
- `newsletter/` 아래 신규 Python 모듈 유입 0건을 유지합니다.
- protected path extraction PR마다 관련 contract coverage 또는 ops-safety evidence가 추가됩니다.

검증 명령:
- `python -m scripts.devtools.dev_entrypoint check --full`
- `python -m scripts.devtools.dev_entrypoint ops-safety-check`
- `python3 scripts/architecture/check_import_boundaries.py --mode ratchet`
- `python3 scripts/architecture/check_import_cycles.py`

### B. Docs Truthfulness Sweep

운영 계약:
- active 문서는 현재 CI/support/runtime truth와 같은 현실을 설명해야 합니다.
- 존재하지 않는 경로, deprecated 실행 방법, 이미 폐기된 phase 서술은 active 문서에 남기지 않습니다.

작업 단위:
1. strategy, PRD, tests guide, migration log, supporting dev docs를 `docs/README.md`, `docs/reference/support-policy.md`, `docs/dev/CI_CD_GUIDE.md`, ADR 기준으로 정렬합니다.
2. `apps/experimental/` 외 경로를 현재 구조 설명에서 제거합니다.
3. deprecated historical test-runner 예시를 active 문서에서 제거하고, canonical entrypoint 또는 직접 `pytest` 예시로 대체합니다.
4. web operator surface, CLI/automation 보조 surface, scheduler/preset/approval/source-policy/history 현실을 문서에 반영합니다.

완료 기준:
- active Markdown 문서에서 존재하지 않는 `apps/*` wrapper 경로 재참조 0건
- active Markdown 문서에서 deprecated historical test-runner 실행 예시 0건
- strategy / PRD / tests guide / migration log / development guide가 같은 현재 상태를 설명

검증 명령:
- `python -m scripts.devtools.dev_entrypoint docs-check`
- `rg -n "apps/(cli|web|worker|scheduler)" docs tests README.md -g '*.md'`
- active Markdown 대상 grep으로 deprecated test-runner command 예시가 남아 있지 않은지 확인

### C. Ops-Safety / Observability

운영 계약:
- 운영 안정성 판단은 문구가 아니라 게이트와 smoke 결과로 합니다.
- idempotency / outbox / scheduler retry safety는 구조 리팩토링보다 우선합니다.

작업 단위:
1. 다음 운영 지표를 release / hotspot reduction review 기준으로 문서화하고 유지합니다.
2. protected path PR은 어떤 지표가 유지됐는지 PR evidence에 남깁니다.
3. live smoke와 local gate 결과를 release 전 증빙으로 남기는 운영 습관을 고정합니다.

완료 기준:
- `check --full` 또는 동등 full gate의 최근 실행 결과를 release 판단 근거로 사용
- scheduler retry safety는 `tests/integration/test_schedule_execution.py` 와 `tests/unit_tests/test_schedule_time_sync.py` 결과로 확인
- dedupe/outbox regressions 는 `tests/contract/test_web_email_routes_contract.py` 와 관련 smoke 결과로 추적
- live smoke 결과는 `python -m scripts.devtools.dev_entrypoint smoke web` 또는 `make ops-safety-smoke` 증빙으로 기록

검증 명령:
- `python -m scripts.devtools.dev_entrypoint check --full`
- `python -m scripts.devtools.dev_entrypoint smoke web`
- `python -m scripts.devtools.dev_entrypoint ops-safety-check`

## 5) Success Metrics

다음 90일은 루트 엔트리 수보다 legacy reduction과 운영 판단 지표를 우선 KPI로 사용합니다.

| 영역 | Baseline (2026-03-10) | 목표 방향 | 운영 판단 기준 |
|---|---|---|---|
| tracked root entries | 30 | 유지 | 30 이하 유지, repo hygiene strict green |
| `newsletter/` Python 파일 수 | 50 | 감소 | 신규 파일 유입 0, 기존 파일 수 감소 |
| `newsletter/` Python LOC | 12511 | 감소 | extraction PR 누적 기준 감소 |
| `newsletter_core/` 활용 비중 | public facade 중심 | 증가 | 신규 기능 추가 위치가 `newsletter_core/` 인지 확인 |
| `web/routes_generation.py` LOC | 1084 | 감소 | route-binding 외 책임 분리 |
| `newsletter/tools.py` LOC | 926 | 감소 | legacy helper 축소 |
| `newsletter/llm_factory.py` LOC | 848 | 감소 | provider/runtime config 분리 |
| `newsletter/graph.py` LOC | 705 | 감소 | orchestration wrapper 축소 |
| `web/static/js/app.js` LOC | 2270 | 감소 | operator flow 단위 분리 |
| protected path contract coverage | 현재 필수 suite 5종 | 증가 | extraction 전에 tests/contract 또는 ops-safety evidence 추가 |
| full gate health | `check --full` 기준 | 유지/개선 | 최근 release candidate / hotspot PR 기준 green 유지 |
| scheduler retry safety | required suites 존재 | 유지/개선 | 관련 suite failure 시 reduction PR 중단 |
| dedupe/outbox incident 수 | release 기준 추적 | 0 unresolved | duplicate send regression 발생 시 다음 배치를 ops-safety 우선으로 전환 |
| live smoke 결과 | source web smoke 사용 가능 | green 유지 | release 전 latest smoke evidence 필요 |

## 6) Out of Scope

이 문서가 다음 90일 우선순위에서 다루지 않는 항목입니다.

- root cleanup 재확대 또는 루트 구조 대청소 재개
- 새로운 app surface 발명
- RAG, 모바일 앱, 신규 배포 채널 추가
- support policy / packaging policy / platform support 재정의
- runtime/business logic 대규모 재설계
- `newsletter/` 를 확장하는 방향의 구현

## 7) 롤백 원칙

- 문서/정책 정렬 작업으로 CI truth와 충돌이 생기면, support policy / CI guide / ADR 기준으로 문서를 즉시 되돌립니다.
- legacy reduction 배치에서 ops-safety suite가 깨지면, extraction을 되돌리고 기존 contract를 우선 복구합니다.
- repo hygiene 예외 추가가 필요하면 예외 사유와 제거 목표 시점을 정책 문서와 함께 기록합니다.
