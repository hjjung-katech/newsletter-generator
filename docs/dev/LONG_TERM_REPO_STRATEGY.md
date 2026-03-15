# Long-term Repo Strategy & Operating Playbook

이 문서는 현재 저장소 상태를 기준으로 리포 구조/운영 우선순위를 정렬하는 장기 정본(SSOT)입니다.
새로운 지원 정책이나 제품 비전을 정의하지 않고, 이미 운영 중인 계약을 현재 현실에 맞게 고정합니다.

- 기준일: 2026-03-15
- 적용 범위: repo structure, docs truthfulness, legacy surface reduction, ops observability
- 선행 정본:
  - `docs/reference/support-policy.md`
  - `docs/technical/adr-0001-architecture-boundaries.md`
  - `docs/dev/CI_CD_GUIDE.md`
  - `docs/dev/REPO_HYGIENE_POLICY.md`
  - `docs/README.md`

## 0) Strategy Close-out Declaration

2026-03-15 기준 legacy burn-down 및 운영 완성도 전략 실행은 공식 close-out 상태로 전환합니다.

- 완료된 축:
  - docs truth alignment
  - repo hygiene hard gate / strict audit baseline
  - hotspot burn-down 및 maintenance mode 전환
  - schedule/history, approval, preset, source policy, personalization visibility 정렬
  - settings provenance, mismatch diagnostics, field-level explanation, lineage summary/detail baseline
- 현재 baseline 이후의 기본 운영 방식:
  - 기계적 extraction 재개 금지
  - maintenance mode 대상은 예외적 reopen 조건에서만 수정
  - optional backlog는 구현 약속이 아니라 backlog 로만 유지
- 이 문서는 close-out 이후의 공식 운영 기준선과 maintenance mode 운영 원칙을 함께 선언합니다.

## 1) 운영 계약 (Current Operating Contract)

이 문서는 아래 계약을 다시 정의하지 않습니다. close-out 이후 작업은 모두 이 계약 안에서 수행합니다.

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

- `repo_audit.py --strict` 기준 top-level entries는 2026-03-15 close-out 시점 36개이며 warnings 는 0건입니다.
- 루트 실행 스크립트 분산 문제는 대부분 정리되었고, repo hygiene hard gate가 이를 유지합니다.
- docs hub, support policy, ADR, CI guide가 이미 active 정본으로 운영 중입니다.
- 현재 제품 표면은 실질적으로 Flask web 운영 표면 중심이며, CLI/scheduler/automation이 이를 보조합니다.
- 남아 있는 구조 부채의 중심은 root clutter가 아니라 legacy runtime hotspot 이지만, 2026-03-15 기준으로는 추가 기계적 burn-down보다 maintenance mode 유지가 우선입니다.

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

- root cleanup 1차 안정화
  - top-level entry 수 자체를 더 줄이는 단계는 아니지만, repo hygiene strict gate 기준 warnings 0 상태를 유지합니다.
- repo hygiene hard gate 운영
  - strict audit와 artifact 업로드가 CI에 이미 연결돼 있습니다.
- docs hub / canonical docs 운영
  - `docs/README.md` 중심 정본 체계가 활성화돼 있습니다.
- architecture guardrail 운영
  - ADR, import boundary ratchet, legacy surface manifest가 활성 상태입니다.
- canonical developer entrypoint 정규화
  - contributor-facing run/check flow는 `python -m scripts.devtools.dev_entrypoint ...` 로 정리되었습니다.
- legacy hotspot burn-down 종료
  - `newsletter/llm_factory.py`, `newsletter/tools.py`, `newsletter/graph.py`, `web/routes_generation.py`, `web/static/js/app.js` 는 maintenance mode 대상으로 고정합니다.
- 운영 완성도 visibility 정렬 완료
  - schedule/history, approval, preset, source policy, personalization, settings provenance, mismatch diagnostics surface를 additive helper 경계로 정렬했습니다.
  - field-level explanation과 lineage summary/detail까지 현재 baseline에 포함되며, 추가 drill-down은 optional backlog로만 남깁니다.

이 문서의 다음 우선순위는 root cleanup 재개나 추가 기계적 extraction이 아니라, 현재 achieved state를 baseline으로 고정하고 maintenance mode 원칙으로 운영하는 것입니다.

## 4) Maintenance Mode Operating Rules

### A. 공식 maintenance mode 대상

운영 계약:
- 신규 기능은 `newsletter_core/` 에만 누적합니다.
- maintenance mode 대상은 다음 다섯 개 hotspot 입니다.
  - `newsletter/llm_factory.py`
  - `newsletter/tools.py`
  - `newsletter/graph.py`
  - `web/routes_generation.py`
  - `web/static/js/app.js`
- 이 경계는 bug fix, contract alignment, helper reconnect, 작은 운영 완성도 보강 외에는 다시 구조 변경 대상으로 취급하지 않습니다.

### B. reopen 조건

다음 조건 중 하나가 있을 때만 maintenance mode 경계를 다시 엽니다.

1. user-facing bug fix 또는 incident 대응 중 동일 hotspot 수정이 직접 필요할 때
2. 새로운 제품 요구가 해당 shell 변경을 직접 요구할 때
3. 중복 로직이 다시 유입되어 maintenance cost가 유의미하게 증가할 때
4. shell LOC 또는 complexity가 다시 유의미하게 증가해 review cost가 커질 때
5. 반복된 운영 해석 요청이 현재 optional backlog 범위를 정당화할 때

reopen 원칙:
- small-batch 로만 진행합니다.
- 먼저 contract / ops-safety suite를 고정합니다.
- semantics 보존이 불확실하면 reduction보다 안정성 복구를 우선합니다.
- reopen 이유가 위 다섯 조건 중 무엇인지 RR 첫머리에 명시되지 않으면 reopen 배치로 취급하지 않습니다.

### C. optional backlog

다음 항목은 선택 과제로만 남기고, 현재 baseline에는 포함하지 않습니다.

- richer causal mismatch diagnostics
- deeper provenance lineage history
- time-based settings/result drill-down
- deeper causal explanation

### D. 유지해야 하는 운영 판단 기준

- `check --full` 또는 동등 full gate green
- repo hygiene strict green
- scheduler retry safety / dedupe / outbox contract 유지
- docs hub, support policy, ADR, strategy, PRD 간 truth alignment 유지

## 5) Success Metrics

close-out 이후 KPI는 추가 burn-down 양보다 현재 baseline을 깨지 않고 유지하는지에 둡니다.

| 영역 | Baseline (2026-03-10) | 목표 방향 | 운영 판단 기준 |
|---|---|---|---|
| repo_audit top-level entries | 36 | 유지 또는 선택적 감소 | strict warnings 0 유지 |
| `newsletter/` Python 파일 수 | 50 | 유지 또는 선택적 감소 | 신규 파일 유입 0, maintenance mode 위반 없는지 확인 |
| `newsletter/` Python LOC | 12511 | 유지 또는 선택적 감소 | reopen 근거 없는 기계적 확장 0건 |
| `newsletter_core/` 활용 비중 | public facade 중심 | 유지/증가 | 신규 기능 추가 위치가 `newsletter_core/` 인지 확인 |
| hotspot shell 수 | 5 | 유지 | maintenance mode 대상 목록이 문서/리뷰 기준으로 유지됨 |
| protected path contract coverage | 현재 필수 suite 5종 + docs/repo hygiene gate | 유지/증가 | protected path 수정 시 관련 evidence가 빠지지 않는지 확인 |
| full gate health | `check --full` 기준 | 유지 | main/close-out 이후 green 유지 |
| scheduler retry safety | required suites 존재 | 유지/개선 | 관련 suite failure 시 reduction PR 중단 |
| dedupe/outbox incident 수 | release 기준 추적 | 0 unresolved | duplicate send regression 발생 시 다음 배치를 ops-safety 우선으로 전환 |
| visibility/provenance surface | additive helper 경계 존재 | 유지 | schedule/history/approval/preset/source policy/personalization/settings diagnostics/lineage 의미 일관성 유지 |
| live smoke 결과 | source web smoke 사용 가능 | green 유지 | release 전 latest smoke evidence 필요 |

## 6) Out of Scope

이 문서가 close-out 이후 기본 우선순위로 다루지 않는 항목입니다.

- root cleanup 재확대 또는 루트 구조 대청소 재개
- legacy hotspot 추가 extraction 재개
- 새로운 app surface 발명
- RAG, 모바일 앱, 신규 배포 채널 추가
- support policy / packaging policy / platform support 재정의
- runtime/business logic 대규모 재설계
- `newsletter/` 를 확장하는 방향의 구현

## 7) 롤백 원칙

- 문서/정책 정렬 작업으로 CI truth와 충돌이 생기면, support policy / CI guide / ADR 기준으로 문서를 즉시 되돌립니다.
- maintenance mode 경계 재오픈 배치에서 ops-safety suite가 깨지면, reduction을 되돌리고 기존 contract를 우선 복구합니다.
- repo hygiene 예외 추가가 필요하면 예외 사유와 제거 목표 시점을 정책 문서와 함께 기록합니다.
