# Newsletter Generator 테스트 실행 가이드

이 문서는 `tests/README.md` 를 보조하는 실행 요약입니다.
정본 workflow는 `docs/dev/CI_CD_GUIDE.md`, 테스트 분류와 기본 명령은 `tests/README.md` 를 따릅니다.

## 권장 실행 순서

### 1. 일반 개발

```bash
python -m scripts.devtools.dev_entrypoint check
```

### 2. PR 전 전체 검증

```bash
python -m scripts.devtools.dev_entrypoint check --full
```

### 3. ops-safety 관련 변경

```bash
python -m scripts.devtools.dev_entrypoint ops-safety-check
```

### 4. 직접 pytest가 필요한 경우

```bash
python -m pytest tests/unit_tests/ -v
python -m pytest tests/contract/ -q
RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/ -q
```

### 5. E2E 또는 웹 의존 시나리오

```bash
# Terminal 1
python -m scripts.devtools.dev_entrypoint run web

# Terminal 2
python -m pytest tests/e2e/ -v
```

## 빠른 판단 기준

- 단일 변경 검증: `check`
- PR 제출 전: `check --full`
- scheduler / dedupe / config / protected path 변경: `ops-safety-check`
- 문서 변경 포함 시: `python -m scripts.devtools.dev_entrypoint docs-check`

## 문제 해결

### integration이 skip 되는 경우

- `RUN_INTEGRATION_TESTS=1` 이 빠졌는지 확인합니다.
- full gate가 목적이면 개별 명령보다 `check --full` 을 우선 사용합니다.

### E2E 연결 오류

- `python -m scripts.devtools.dev_entrypoint run web` 로 웹 런타임을 띄웠는지 확인합니다.
- `TEST_BASE_URL` 이 실제 주소와 일치하는지 확인합니다.
- 필요하면 `python -m scripts.devtools.dev_entrypoint smoke web` 를 먼저 실행합니다.

## 메모

- historical `scripts/devtools/run_tests.py` 예시는 active 실행 표준이 아닙니다.
- coverage는 artifact로 추적하며, 고정 퍼센트 임계치보다 current gate green을 우선합니다.
