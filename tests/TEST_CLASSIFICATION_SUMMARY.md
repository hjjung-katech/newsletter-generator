# Test Classification Summary

이 문서는 현재 저장소의 테스트 카테고리와 대표 실행 명령을 요약합니다.
정본은 `tests/README.md` 와 `docs/dev/CI_CD_GUIDE.md` 입니다.

## Category Summary

| Category | Purpose | Typical Command |
|---|---|---|
| `unit_tests/` | 함수/모듈/세부 회귀 | `python -m pytest tests/unit_tests/ -v` |
| `contract/` | API / docs / packaging / workflow truth 고정 | `python -m pytest tests/contract/ -q` |
| `integration/` | scheduler/runtime 상호작용 | `RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/ -q` |
| `api_tests/` | API 중심 시나리오 | `python -m pytest tests/api_tests/ -q` |
| `e2e/` | 별도 웹 런타임 필요 | `python -m scripts.devtools.dev_entrypoint run web` 후 `python -m pytest tests/e2e/ -v` |
| `deployment/` | 배포 대상 검증 | 환경별 smoke script 또는 deployment pytest |
| `manual/` | 수동 확인 필요 | `python -m pytest tests/manual/ -v -m manual` |

## Contributor-facing Gate Mapping

| Need | Canonical Command |
|---|---|
| 빠른 로컬 검증 | `python -m scripts.devtools.dev_entrypoint check` |
| PR 전 전체 검증 | `python -m scripts.devtools.dev_entrypoint check --full` |
| ops-safety 보호 경로 검증 | `python -m scripts.devtools.dev_entrypoint ops-safety-check` |
| 문서 품질 확인 | `python -m scripts.devtools.dev_entrypoint docs-check` |

## Current Notes

- `scripts/devtools/run_tests.py` 예시는 더 이상 active 표준이 아닙니다.
- protected path 변경은 scheduler/time-sync/web email/config import side-effect suites를 함께 확인합니다.
- coverage는 artifact와 gate 결과 중심으로 추적하며, 이 문서에서 고정 퍼센트 임계치를 약속하지 않습니다.
