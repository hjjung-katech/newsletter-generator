# Refactoring Execution Plan

기준일: 2026-03-08

이 문서는 현재 코드 상태를 기준으로 리팩토링 업무단위, 단계, 우선순위 근거를 다시 정리한 실행 문서입니다.
장기 방향은 `docs/dev/LONG_TERM_REPO_STRATEGY.md`를 따르고, 본 문서는 그 전략을 당장 실행 가능한 작업 배치로 쪼개는 데 목적이 있습니다.

## 1. 실행 기준

1. 운영 안전이 미관보다 우선이다.
2. 한 PR은 가급적 300 LOC, 8 files 이내의 작은 배치로 유지한다.
3. 계약 테스트와 ops-safety 게이트를 깨는 구조 변경은 금지한다.
4. Web runtime은 다음 제약을 유지한다.
   - `newsletter_core.public.generation.generate_newsletter`를 사용한다.
   - sync/async/fallback 경로는 공통 DB state-transition 함수를 공유한다.
   - 응답 스키마 `status`, `html_content`, `title`, `generation_stats`, `input_params`, `error`를 유지한다.
   - runtime code에 새로운 동적 모듈 로딩을 추가하지 않는다.
5. 설정은 `newsletter/centralized_settings.py`를 단일 진실 공급원으로 두고, `newsletter/config_manager.py`는 얇은 호환 어댑터로 수렴시킨다.

## 2. 현재 상태 스냅샷

2026-03-08 기준 로컬 검증 결과:

- `make check`: PASS
- `make check-full`: PASS
- preflight, docs-check, skills-check, ops-safety-check: PASS

현재 대형 파일 상위권(`wc -l` 기준):

| 파일 | 라인 수 | 판단 |
|---|---:|---|
| `web/static/js/app.js` | 2270 | 가장 크지만 백엔드 계약 안정화 이후 착수하는 편이 안전 |
| `web/db_state.py` | 1433 | idempotency/outbox/history를 품은 핵심 운영 리스크 |
| `newsletter_core/application/generation/compose.py` | 1119 | 도메인 조합 로직 집중, 후속 핵심 후보 |
| `web/routes_generation.py` | 958 | 요청 검증, job orchestration, 스케줄 처리가 섞여 있음 |
| `web/schedule_runner.py` | 707 | 스케줄 안정성 핵심, `db_state` 분리와 강하게 결합 |
| `newsletter/config_manager.py` | 375 | "thin compatibility adapter" 목표 대비 책임 과다 |
| `web/app.py` | 316 | 이전 우선 대상이었지만 지금은 bootstrap 정리 수준 |
| `newsletter/cli.py` | 258 | 이미 1차 분해가 진행돼 우선순위 하락 |
| `newsletter/chains.py` | 158 | 이미 많이 축소돼 우선순위 하락 |

추가 관찰:

- `web/routes_generation.py`는 아직 `importlib.util.spec_from_file_location` 기반 동적 로딩을 사용한다.
- `web/app.py`는 `sys.path` 조작과 fallback import가 반복된다.
- `docs/archive/2026-q1/F14_COMPLETION_REPORT.md`에는 당시 Settings 작업 완료 보고서와 미완료 항목 이력이 함께 남아 있다.

## 3. 우선순위 기준과 근거

우선순위는 아래 순서로 결정한다.

1. 운영 장애 가능성
   - scheduler, idempotency, outbox, config SSOT를 건드리는 파일을 먼저 정리한다.
2. 제약 위반 또는 구조 경계 누수
   - 동적 로딩, 과도한 import fallback, import-time side effect 가능성은 조기 제거 대상이다.
3. 변경 파급도
   - 여러 경로가 공용으로 의존하는 모듈은 먼저 분해해야 후속 작업이 쉬워진다.
4. 테스트 가능성
   - 계약 테스트/ops-safety 테스트로 보호할 수 있는 영역부터 쪼개는 편이 안전하다.
5. 순수 규모
   - 단순히 큰 파일이라는 이유만으로 최우선으로 올리지 않는다.

## 4. 현재 우선순위 백로그

### P0. 리팩토링 시작 전에 잠가야 할 기반

#### WU-0. 테스트/계약 잠금

- 목표
  - 현재 동작을 더 명확하게 고정한 뒤 리팩토링한다.
- 포함 작업
  - Settings unit test 보강: happy path, 필수값 누락, 타입 오류, secret masking
  - `routes_generation` 핵심 응답 shape와 dedupe 동작 확인
  - 현재 ops-safety 필수 테스트 목록을 문서/PR 템플릿에 명시
- 우선 근거
  - 설정과 웹 런타임은 ops-safety-sensitive 경로이며, 테스트 잠금 없이 분해하면 회귀 탐지가 늦어진다.
- 완료 조건
  - 관련 테스트가 추가되거나 기존 게이트로 충분히 보호된다는 근거가 문서화된다.

### P1. 웹 런타임 안정화

#### WU-1. `web/routes_generation.py` 분해

- 목표
  - generation 라우트 파일에서 요청 검증, job orchestration, 스케줄/히스토리 응답 직렬화 책임을 분리한다.
- 포함 작업
  - request parsing/validation helper 추출
  - job submission/idempotency 흐름 service 추출
  - schedule/history response serializer 추출
  - 동적 로딩 제거 후 정적 import 경로로 전환
- 우선 근거
  - Web runtime 제약 위반이 직접 존재하고, generation API는 사용자 영향이 가장 큰 진입점이다.
  - idempotency와 response schema를 동시에 다루므로 후속 작업의 기준점 역할을 한다.
- 제안 slice
  1. 검증 로직 추출 + 동적 로딩 제거
  2. generate/send path의 job orchestration 추출
  3. schedule/history 관련 핸들러 정리
- 검증
  - `make check-full`
  - `pytest tests/test_web_api.py -q`
  - `pytest tests/contract/test_web_email_routes_contract.py -q`
- 롤백
  - route 등록 구조만 되돌리고, 추출한 helper/service는 미사용 상태로 남기지 않고 함께 롤백한다.

#### WU-2. `newsletter/config_manager.py` 축소

- 목표
  - 설정 접근 경로를 중앙집중식 설정으로 더 수렴시키고, YAML/기본값 병합 책임을 분리한다.
- 포함 작업
  - runtime env 접근과 config file 로딩 책임 분리
  - 레거시 경로 fallback은 유지하되 adapter surface를 최소화
  - 테스트 reset/test mode 동작 정리
- 우선 근거
  - repo policy상 `config_manager.py`는 thin adapter여야 하며, 현재는 캐시/파일 로딩/기본값 병합까지 들고 있다.
  - 이 영역이 정리되어야 후속 runtime cleanup에서 설정 참조 일관성을 확보할 수 있다.
- 제안 slice
  1. 파일 로더/기본값 병합 책임 분리
  2. adapter public surface 축소
  3. settings unit test와 compatibility test 보강
- 검증
  - `make check-full`
  - `pytest tests/unit_tests/test_config_import_side_effects.py -q`
- 롤백
  - adapter surface를 유지한 채 내부 위임만 복구한다.

#### WU-3. `web/app.py` bootstrap 정리

- 목표
  - app bootstrap을 route registration 중심으로 단순화하고 `sys.path` 조작을 줄인다.
- 포함 작업
  - bootstrap/init 함수 추출
  - import fallback 최소화
  - route registration과 runtime setup을 분리
- 우선 근거
  - 예전 대형 파일이었지만 현재는 크기보다 경계 정리가 핵심이다.
  - `routes_generation` 분해가 끝난 뒤에 처리해야 충돌이 적다.
- 검증
  - `make check-full`
  - `pytest tests/test_web_api.py -q`

### P2. 운영 상태 저장소와 스케줄러 분리

#### WU-4. `web/db_state.py` 도메인별 분할

- 목표
  - 1,400+ 라인 상태 저장소를 schema, history/idempotency, archive/analytics, presets/source policies 단위로 분리한다.
- 포함 작업
  - schema/bootstrap 함수 분리
  - history/job/idempotency 함수 분리
  - archive/preset/source policy 함수 분리
  - 기존 import path를 유지할 re-export 또는 shim 제공
- 우선 근거
  - idempotency/outbox는 장기 전략 문서가 가장 먼저 잠그라고 한 운영 안전 핵심이다.
  - `schedule_runner`, `routes_generation`, approval/email route가 공통으로 의존하므로 선행 정리가 필요하다.
- 제안 slice
  1. schema + connection helper
  2. history/idempotency
  3. archive/analytics
  4. presets/source policies
- 검증
  - `make check-full`
  - `pytest tests/integration/test_schedule_execution.py -q`
  - `pytest tests/unit_tests/test_schedule_time_sync.py -q`
  - `pytest tests/contract/test_web_email_routes_contract.py -q`
- 롤백
  - re-export layer를 남겨 import 경로를 즉시 복원할 수 있게 한다.

#### WU-5. `web/schedule_runner.py` 분해

- 목표
  - RRULE 계산, pending scan, enqueue, reschedule, telemetry를 분리한다.
- 포함 작업
  - time window 계산 helper 추출
  - due schedule scan과 reschedule 분리
  - enqueue path를 공통 job creation 흐름에 더 명확히 연결
- 우선 근거
  - 스케줄러는 운영 사고 빈도가 높은 영역이며 `db_state` 분리 없이는 안전하게 손대기 어렵다.
- 선행 조건
  - WU-4 완료
- 검증
  - `make check-full`
  - `pytest tests/integration/test_schedule_execution.py -q`
  - `pytest tests/unit_tests/test_schedule_time_sync.py -q`

### P3. 도메인 조합 로직 정리

#### WU-6. `newsletter_core/application/generation/compose.py` 분해

- 목표
  - 입력 정규화, 섹션 조합, HTML payload assembly, 보조 메타데이터 계산을 분리한다.
- 포함 작업
  - pure function 경계 확대
  - 외부 의존성 호출과 템플릿 조립 경계 분리
  - 테스트 작성이 쉬운 구조로 재배치
- 우선 근거
  - 크기가 크고 도메인 규칙이 밀집돼 있지만, web runtime 안정화보다 한 단계 뒤에 해도 된다.
- 검증
  - `make check-full`
  - generation smoke/contract 관련 테스트

### P4. UI/CLI 후속 정리

#### WU-7. `web/static/js/app.js` 모듈화

- 목표
  - API client, state store, DOM binding, feature modules를 분리한다.
- 우선 근거
  - 가장 큰 파일이지만, backend API shape가 먼저 안정돼야 재작업을 줄일 수 있다.
- 선행 조건
  - WU-1 완료

#### WU-8. CLI 잔여 정리

- 대상
  - `newsletter/cli.py`
  - `newsletter/cli_diagnostics.py`
  - `newsletter/cli_run.py`
  - `newsletter/cli_test.py`
- 우선 근거
  - 구 문서에서는 최상위 대상이었지만, 현재는 웹 런타임과 설정 정리보다 ROI가 낮다.

## 5. 단계별 실행 순서

### Phase 0. 기준선 잠금

1. WU-0 실행
2. 현재 게이트/테스트 매트릭스 문서화
3. 리팩토링 PR 템플릿에 검증 명령과 롤백 항목 고정

### Phase 1. 웹 런타임 1차 안정화

1. WU-1 `routes_generation`
2. WU-2 `config_manager`
3. WU-3 `web/app`

### Phase 2. 상태 저장소와 스케줄러

1. WU-4 `db_state`
2. WU-5 `schedule_runner`

### Phase 3. 도메인 조합 로직

1. WU-6 `compose.py`

### Phase 4. 후속 사용자 경험 정리

1. WU-7 `app.js`
2. WU-8 CLI

## 6. 업무단위별 산출물 형식

각 업무단위는 아래 산출물을 남긴다.

1. RR 또는 작업 요청 링크
2. 대상 파일과 제외 파일
3. 리스크 요약
4. 롤백 방법
5. 실행한 검증 명령과 결과
6. 후속 업무로 넘길 미해결 항목

## 7. 이번 주 바로 시작할 순서

1. WU-0 중 Settings unit test 미완료 항목을 먼저 정리한다.
2. `web/routes_generation.py`에서 동적 로딩 제거와 validation helper 추출을 첫 PR로 진행한다.
3. 같은 흐름에서 `job orchestration` 추출을 두 번째 PR로 진행한다.
4. 이후 `newsletter/config_manager.py`를 thin adapter 방향으로 줄인다.
5. 그 다음 `web/db_state.py` 분해에 착수한다.

## 8. 지금 하지 않을 것

- `newsletter/chains.py` 재분해
  - 이미 많이 줄어 우선순위가 낮다.
- `web/static/js/app.js` 선행 리팩토링
  - backend API shape가 더 안정된 뒤 진행하는 편이 낫다.
- 대규모 rename 또는 디렉터리 재배치
  - 현재 단계에서는 운영 안전성 대비 효익이 낮다.

## 9. Definition of Done

각 slice는 아래를 만족해야 완료로 본다.

- 기능 회귀 없음
- 필요한 경우 ops-safety 필수 테스트 통과
- `make check-full` 통과
- 변경 이유, 리스크, 롤백 절차 기록
- 다음 slice를 막는 기술 부채를 새로 만들지 않음
