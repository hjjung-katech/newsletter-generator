# Newsletter Generator 테스트 가이드

이 문서는 현재 저장소의 테스트 실행 현실을 설명하는 active 가이드입니다.
정본 gate 계약은 `docs/dev/CI_CD_GUIDE.md` 를 따르며, 이 문서는 테스트 분류와 실행 예시를 보조합니다.

## 현재 테스트 구조

```text
tests/
├── unit_tests/      # 단위 테스트 및 web/db 세부 회귀
├── integration/     # scheduler/runtime 통합 시나리오
├── contract/        # facade / web runtime / packaging / workflow truth 고정
├── api_tests/       # 외부 API 또는 API 중심 시나리오
├── e2e/             # 수동 또는 별도 웹 런타임이 필요한 흐름
├── deployment/      # 배포 대상 smoke / release 검증
├── manual/          # 수동 테스트
└── test_data/       # 테스트 데이터
```

## canonical 실행 경로

로컬 contributor-facing 기준 명령은 `python -m scripts.devtools.dev_entrypoint` 입니다.
`make check`, `make check-full` 는 같은 경로를 호출하는 thin wrapper입니다.

### 빠른 로컬 게이트

```bash
python -m scripts.devtools.dev_entrypoint check
```

포함 범위:

- release preflight
- quick CI checks
- docs checks
- newsletter smoke
- web smoke
- scheduler smoke

### PR 전 전체 게이트

```bash
python -m scripts.devtools.dev_entrypoint check --full
```

추가 범위:

- full CI checks
- ops-safety required suites

### ops-safety 전용

```bash
python -m scripts.devtools.dev_entrypoint ops-safety-check
```

## 직접 실행할 때의 현재 기준

### 단위 테스트

```bash
python -m pytest tests/unit_tests/ -v
```

### contract 테스트

```bash
python -m pytest tests/contract/ -q
```

### integration 테스트

```bash
RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/ -q
```

### scheduler / ops-safety 핵심 경로

```bash
python -m pytest tests/integration/test_schedule_execution.py -q
python -m pytest tests/unit_tests/test_schedule_time_sync.py -q
python -m pytest tests/contract/test_web_email_routes_contract.py -q
python -m pytest tests/test_web_api.py -q
python -m pytest tests/unit_tests/test_config_import_side_effects.py -q
```

### E2E 또는 수동 웹 흐름

```bash
# Terminal 1
python -m scripts.devtools.dev_entrypoint run web

# Terminal 2
python -m pytest tests/e2e/ -v
```

배포/실서비스 검증은 `tests/deployment/` 스크립트와 운영 환경 변수를 따릅니다.

## 테스트 카테고리 해석

- `unit`: 함수/클래스/모듈 단위 회귀
- `integration`: scheduler/runtime 상호작용 검증
- `contract`: 문서/경계/API truth를 고정하는 회귀
- `mock_api`: 외부 의존성을 모킹한 테스트
- `real_api`: 실제 API 키가 필요한 테스트
- `manual`, `e2e`, `deployment`: 별도 환경 또는 수동 절차가 필요한 테스트

## 환경 변수 메모

### 기본 제어

- `RUN_INTEGRATION_TESTS=1`: integration 테스트 활성화
- `RUN_REAL_API_TESTS=1`: 실제 API 테스트 활성화
- `TEST_EMAIL_RECIPIENT`: 이메일 테스트 수신자

### E2E / 배포

- `TEST_BASE_URL`: E2E 대상 URL
- `RAILWAY_PRODUCTION_URL`: Railway 배포 URL
- `DEPLOYED_URL`: 일반 배포 URL

### API 키

- `GEMINI_API_KEY`
- `SERPER_API_KEY`
- `POSTMARK_SERVER_TOKEN`
- `EMAIL_SENDER`

## 품질 기준

- 현재 contributor gate는 고정 커버리지 퍼센트보다 `check --full` green과 contract/ops-safety 결과를 우선합니다.
- coverage artifact는 `.local/coverage/` 아래에 생성되며, 별도 개선 작업 없이 hard threshold를 약속하지 않습니다.
- protected path 변경은 관련 contract 또는 ops-safety evidence를 함께 남겨야 합니다.

## 문제 해결

### E2E 연결 오류

```text
httpx.ConnectError: connection refused
```

확인 순서:

1. `python -m scripts.devtools.dev_entrypoint run web` 로 웹 런타임이 떠 있는지 확인
2. `TEST_BASE_URL` 값이 실제 런타임 주소와 맞는지 확인
3. 필요 시 `python -m scripts.devtools.dev_entrypoint smoke web` 로 source web smoke를 먼저 실행

### integration이 skip 되는 경우

- `RUN_INTEGRATION_TESTS=1` 이 설정되지 않았을 수 있습니다.
- 필요한 dummy/mock env가 없는 경우 `python -m scripts.devtools.dev_entrypoint check --full` 경로를 우선 사용하세요.

## Supporting Docs

- current CI / required checks: `docs/dev/CI_CD_GUIDE.md`
- active test execution summary: `tests/TEST_EXECUTION_GUIDE.md`
- category snapshot: `tests/TEST_CLASSIFICATION_SUMMARY.md`
- archived QA summary: `tests/archive/RESULTS_SUMMARY.md`
