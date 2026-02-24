# Local CI Verification Guide

로컬에서 GitHub Actions와 동일한 기준으로 검증하는 표준 가이드입니다.

## Quick Start

```bash
cd /Users/hojungjung/development/newsletter-generator
make bootstrap
make doctor
make check
```

PR 전 최종 검증:

```bash
make check-full
```

## Standard Commands

| Command | Purpose | When |
|---|---|---|
| `make doctor` | 작업 경로/인터프리터 전제 조건 검증 | 새 터미널 시작 시 |
| `make check` | 빠른 표준 게이트 (`test-quick + docs-check + skills-check`) | 개발 중 반복 |
| `make check-full` | 전체 PR 게이트 (`test-full + docs-check + skills-check`) | 푸시/PR 전 |
| `make ci-fix` | 포맷 자동 수정 포함 CI 스크립트 실행 | 코드 정리 필요 시 |
| `make docs-check` | Markdown 링크/스타일 검증 | 문서 변경 시 |

## Strict Gate Policy

현재 게이트는 fail-fast 정책입니다.

- `mypy` 실패 시 전체 실패
- `bandit` 실패 시 전체 실패
- 단위 테스트 실패 시 전체 실패

경고만 출력하고 통과시키는 정책은 사용하지 않습니다.

## Under the Hood

- 주 게이트 스크립트: `run_ci_checks.py`
- 실행 엔트리: `Makefile`의 `check`, `check-full`
- 아키텍처 경계 검사: `scripts/architecture/check_import_boundaries.py`
- import cycle 검사: `scripts/architecture/check_import_cycles.py`

## Common Failures

### 1) Wrong working directory

현상:
- `make doctor`에서 cwd 불일치 실패

해결:
```bash
cd /Users/hojungjung/development/newsletter-generator
make doctor
```

### 2) Virtualenv/interpreter mismatch

현상:
- `.venv/bin/python` 없음
- 도구(black/isort/flake8/mypy/bandit/pytest) import 실패

해결:
```bash
make bootstrap
make doctor
```

### 3) Formatting/lint failures

해결:
```bash
make ci-fix
make check
```

### 4) Architecture boundary/cycle failures

진단:
```bash
.venv/bin/python scripts/architecture/check_import_boundaries.py --mode ratchet
.venv/bin/python scripts/architecture/check_import_cycles.py
```

## Recommended Local Workflow

```bash
# 1) 환경 점검
make doctor

# 2) 반복 개발 루프
make check

# 3) PR 직전 최종 게이트
make check-full
```
