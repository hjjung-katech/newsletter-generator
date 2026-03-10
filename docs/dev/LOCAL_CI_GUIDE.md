# Local CI Verification Guide

로컬에서 GitHub Actions와 동일한 기준으로 검증하는 표준 가이드입니다.

## Quick Start

```bash
cd newsletter-generator
python -m scripts.devtools.dev_entrypoint bootstrap
python -m scripts.devtools.dev_entrypoint doctor
python -m scripts.devtools.dev_entrypoint check
```

기본 로컬 가상환경 경로는 `.local/venv/` 입니다. 기존 clone의 루트 `.venv/` 는 호환 fallback으로만 지원합니다.

PR 전 최종 검증:

```bash
python -m scripts.devtools.dev_entrypoint check --full
```

## Standard Commands

| Command | Purpose | When |
|---|---|---|
| `python -m scripts.devtools.dev_entrypoint doctor` | 작업 경로/인터프리터 전제 조건 검증 | 새 터미널 시작 시 |
| `python -m scripts.devtools.dev_entrypoint check` | 빠른 표준 게이트 (`test-quick + docs-check + skills-check`) | 개발 중 반복 |
| `python -m scripts.devtools.dev_entrypoint check --full` | 전체 PR 게이트 (`test-full + docs-check + skills-check`) | 푸시/PR 전 |
| `python -m scripts.devtools.dev_entrypoint smoke web` | cross-platform source web smoke | CI smoke 재현 시 |
| `make ci-fix` | 포맷 자동 수정 포함 CI 스크립트 실행 | 코드 정리 필요 시 |
| `make docs-check` | Markdown 링크/스타일 검증 | 문서 변경 시 |
| `make clean-caches` | 재생성 가능한 cache/coverage 삭제 | gate 전후 root 정리 |
| `make clean-local` | cache + `.local` scratch 삭제 | 산출물 정리 |

`make bootstrap`, `make doctor`, `make check`, `make check-full`는 동일한 Python 엔트리포인트를 호출하는 wrapper입니다.

## Strict Gate Policy

현재 게이트는 fail-fast 정책입니다.

- `mypy` 실패 시 전체 실패
- `bandit` 실패 시 전체 실패
- 단위 테스트 실패 시 전체 실패

경고만 출력하고 통과시키는 정책은 사용하지 않습니다.

## Under the Hood

- 주 게이트 스크립트: `run_ci_checks.py`
- 실행 엔트리 정본: `python -m scripts.devtools.dev_entrypoint`
- Make wrapper: `make check`, `make check-full`
- 아키텍처 경계 검사: `scripts/architecture/check_import_boundaries.py`
- import cycle 검사: `scripts/architecture/check_import_cycles.py`

## Common Failures

### 1) Wrong working directory

현상:
- Git checkout 바깥에서 명령 실행

해결:
```bash
cd newsletter-generator
python -m scripts.devtools.dev_entrypoint doctor
```

### 2) Virtualenv/interpreter mismatch

현상:
- `.local/venv/bin/python` 없음
- 도구(black/isort/flake8/mypy/bandit/pytest) import 실패

해결:
```bash
python -m scripts.devtools.dev_entrypoint bootstrap
python -m scripts.devtools.dev_entrypoint doctor
```

### 3) Formatting/lint failures

해결:
```bash
make ci-fix
python -m scripts.devtools.dev_entrypoint check
```

### 4) Architecture boundary/cycle failures

진단:
```bash
$(make print-python) scripts/architecture/check_import_boundaries.py --mode ratchet
$(make print-python) scripts/architecture/check_import_cycles.py
```

## Recommended Local Workflow

```bash
# 1) 환경 점검
python -m scripts.devtools.dev_entrypoint doctor

# 2) 반복 개발 루프
python -m scripts.devtools.dev_entrypoint check

# 3) PR 직전 최종 게이트
python -m scripts.devtools.dev_entrypoint check --full
```
