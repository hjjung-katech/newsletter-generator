# Newsletter Generator 프로젝트 요구사항 문서 (PRD)

이 문서는 현재 저장소 기준의 제품 표면과 우선순위를 정리한 PRD입니다.
새로운 앱 표면이나 지원 정책을 발명하지 않고, 이미 운영 중인 web/CLI/scheduler 현실을 반영합니다.

- 기준일: 2026-03-14
- 제품/플랫폼 계약 정본:
  - `docs/reference/support-policy.md`
  - `docs/reference/web-api.md`
  - `docs/dev/CI_CD_GUIDE.md`
  - `docs/dev/LONG_TERM_REPO_STRATEGY.md`

## 1. 제품 개요

- 제품명: Newsletter Generator
- 목적: 최신 뉴스 수집, AI 요약, HTML 뉴스레터 생성, 이메일 발송, 운영 이력 관리를 지원하는 뉴스레터 운영 도구
- 현재 상태: Flask web runtime이 실질적인 운영 표면이며, CLI/scheduler/automation이 이를 보조합니다.
- 현재 형태: Python 패키지 + Flask source runtime + scheduled/background execution + Windows desktop bundle

## 2. 문제 정의

1. 운영자는 키워드/도메인 기반 뉴스레터를 반복적으로 생성, 검토, 발송해야 합니다.
2. 단일 실행 성공보다 schedule, approval, source policy, preset, history 같은 운영 흐름의 안정성이 더 중요합니다.
3. 현재 구조 부채는 root clutter보다 legacy runtime hotspot에 집중되어 있었고, 2026-03-14 기준으로는 추가 기계적 분해보다 maintenance mode 유지가 더 중요한 단계입니다.

## 3. 현재 제품 표면

### 3.1 운영 표면

| 표면 | 현재 상태 | 설명 |
|---|---|---|
| Web runtime | 주 운영 표면 | 생성, 미리보기, 발송, 프리셋, 승인, 스케줄, 소스 정책, 이력/분석을 다룹니다. |
| CLI | 보조 운영 표면 | 반복 실행, 로컬 디버깅, smoke/automation 경로를 제공합니다. |
| Scheduler / worker | 보조 운영 표면 | 예약 실행, retry safety, dedupe, outbox 흐름을 다룹니다. |
| Archive / analytics | 운영 보조 표면 | 실행 이력 재사용, 검색, 운영 가시성을 제공합니다. |

### 3.2 현재 구현된 핵심 기능

| 기능 ID | 기능 | 상태 | 설명 |
|---|---|---|---|
| FR-01 | 뉴스 수집 | 운영 중 | Serper, RSS, Naver 등 현재 지원 소스를 통합합니다. |
| FR-02 | AI 요약 및 조합 | 운영 중 | LangGraph + multi-LLM 경로로 HTML 뉴스레터를 생성합니다. |
| FR-03 | Web generation flow | 운영 중 | generate / preview / send / archive reference 흐름을 제공합니다. |
| FR-04 | 이메일 발송 | 운영 중 | Postmark 기반 발송과 outbox dedupe를 지원합니다. |
| FR-05 | Schedule workflow | 운영 중 | 예약 실행, preview/run-now, retry safety 경로를 다룹니다. |
| FR-06 | Approval workflow | 운영 중 | 승인 대기함과 상태 전이를 제공합니다. |
| FR-07 | Preset lifecycle | 운영 중 | 저장/갱신/삭제/기본값 관리가 가능합니다. |
| FR-08 | Source policy management | 운영 중 | allow/block 규칙을 운영자가 관리할 수 있습니다. |
| FR-09 | Execution history / archive | 운영 중 | 이전 실행 검색과 참조 흐름을 제공합니다. |
| FR-10 | Analytics / ops visibility | 운영 중 | 기본 분석과 운영 상태 확인 경로를 제공합니다. |

## 4. 현재 제품 목표

| ID | 목표 | 현재 상태 | 성공 기준 |
|---|---|---|---|
| G1 | web 운영 표면에서 주요 작업을 완료 | 진행 중 | generate/preview/send/history/schedule 흐름이 안정적으로 연결됨 |
| G2 | schedule / approval / preset / source policy 흐름 안정화 | 진행 중 | protected path 회귀 0건 유지 |
| G3 | CLI/scheduler/web가 같은 core contract를 공유 | 진행 중 | `newsletter_core.public` 경계 사용 유지 |
| G4 | legacy runtime surface를 maintenance mode로 고정 | 달성 후 유지 단계 | hotspot reopen 조건 없이 기계적 분해가 재개되지 않음 |
| G5 | 운영 계약과 문서 truth를 일치시킴 | 달성 후 유지 단계 | support policy / CI / strategy / PRD가 같은 현실을 설명 |

## 5. 다음 90일 우선순위

이번 PRD는 제품 우선순위를 현재 운영 표면 기준으로 고정하되, close-out 이후에는 maintenance mode 유지와 선택 backlog 구분을 우선합니다.

### 우선순위 상단

1. 운영 안정성 유지
- schedule, approval, preset, source policy, personalization, settings provenance surface의 현재 semantics와 evidence를 유지합니다.

2. maintenance mode 경계 유지
- `newsletter/llm_factory.py`, `newsletter/tools.py`, `newsletter/graph.py`, `web/routes_generation.py`, `web/static/js/app.js` 는 reopen 조건이 없는 한 구조 재작업 대상으로 올리지 않습니다.

3. docs truthfulness 유지
- strategy, PRD, architecture, migration log가 같은 baseline과 같은 종료 판단을 설명하도록 유지합니다.

4. 선택 backlog 관리
- richer mismatch diagnostics, deeper provenance lineage, time-based settings/result drill-down 은 backlog 로만 유지합니다.

reopen 조건:
- user-facing bug fix 또는 incident 대응 중 동일 shell 수정이 직접 필요할 때
- 새로운 제품 요구가 해당 shell 변경을 직접 요구할 때
- 중복 로직 재유입으로 maintenance cost가 다시 커질 때
- shell LOC/complexity가 다시 유의미하게 증가할 때

## 6. 현재 비우선 / 비목표

다음 항목은 현재 우선순위로 올리지 않습니다.

- legacy hotspot 추가 extraction
- deeper settings drill-down 구현
- 벡터 DB RAG
- 새로운 웹/모바일 앱 표면 추가
- 모바일 앱
- 새로운 배포 채널 발명
- support policy / packaging policy 재정의

## 7. 사용 시나리오

### 7.1 운영자 시나리오

```bash
# 로컬 개발/운영 확인
python -m scripts.devtools.dev_entrypoint run web

# CLI 실행 표면
python -m scripts.devtools.dev_entrypoint run newsletter -- run --keywords "AI"
```

운영자는 web 표면에서 다음 작업을 수행합니다.

- 키워드/도메인 기반 생성 및 미리보기
- 프리셋 저장/수정/삭제
- 승인 대기함 검토
- 소스 정책 편집
- 스케줄 생성/관리
- 실행 이력 검색 및 archive reference 재사용

### 7.2 품질/운영 시나리오

```bash
# 빠른 로컬 게이트
python -m scripts.devtools.dev_entrypoint check

# PR 전 전체 게이트
python -m scripts.devtools.dev_entrypoint check --full

# web smoke
python -m scripts.devtools.dev_entrypoint smoke web
```

## 8. 품질 및 운영 기준

### 8.1 품질 게이트

- contributor-facing canonical gate:
  - `python -m scripts.devtools.dev_entrypoint check`
  - `python -m scripts.devtools.dev_entrypoint check --full`
- repo hygiene / docs quality / PR policy / required checks 기준은 `docs/dev/CI_CD_GUIDE.md` 와 `docs/reference/support-policy.md` 를 따릅니다.

### 8.2 운영 판단 지표

다음 항목은 슬로건이 아니라 실제 운영 판단 기준으로 사용합니다.

- `check --full` 또는 동등 full gate 결과
- scheduler retry safety 관련 suite 결과
- dedupe/outbox regression 여부
- source web smoke 또는 deployed ops smoke 결과
- coverage artifact와 contract suite 변동

## 9. 아키텍처 및 구현 제약

- 신규 기능과 점진적 구조 이동의 목표 영역은 `newsletter_core/` 입니다.
- `newsletter/` 와 일부 `web/` hotspot 은 축소 대상이며, 확장 대상이 아닙니다.
- 지원 범위와 packaging 정책은 `docs/reference/support-policy.md` 를 그대로 따릅니다.
- web API 계약은 `docs/reference/web-api.md` 를 따릅니다.

## 10. 문서 및 참조

- 문서 허브: `docs/README.md`
- 지원 계약: `docs/reference/support-policy.md`
- CI / workflow 계약: `docs/dev/CI_CD_GUIDE.md`
- 구조/운영 우선순위: `docs/dev/LONG_TERM_REPO_STRATEGY.md`
- 아키텍처 경계: `docs/technical/adr-0001-architecture-boundaries.md`
