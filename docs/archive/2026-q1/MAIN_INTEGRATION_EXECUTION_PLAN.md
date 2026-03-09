# Main 통합 실행 계획 (현재 상태 기준)

> Historical note (2026-03-09): RR-2에서 archive로 이관된 문서입니다.
> 현재 release 실행 기준은 `docs/dev/CI_CD_GUIDE.md` 와
> `.github/PULL_REQUEST_TEMPLATE/release_integration.md` 를 따릅니다.

본 문서는 2026년 3월 9일 기준으로 release 통합 계획을 정리한 시점 문서입니다.
이전 문서의 전제였던 `baseline/main-equivalent` 기준 분리 통합은 더 이상 기본 실행 경로가 아닙니다.
현재 `main`에는 release/quality/scheduler 관련 RR가 직접 순차 머지되어 있으므로, 이 문서는
`무엇이 이미 main에 흡수되었는지`와 `앞으로 무엇을 새 RR로 다시 열어야 하는지`를 배경 정보로 보존합니다.

## 0) 현재 판단

1. `release/*` 브랜치를 `baseline/main-equivalent`에서 다시 시작하지 않습니다.
2. 기존 release 스트림 대부분은 이미 `main`에 흡수되어 별도 branch integration 작업이 의미를 잃었습니다.
3. 앞으로 release 관련 작업이 필요하면 반드시 **현재 `main` 기준 새 RR/새 branch/새 manifest 검증**으로 다시 엽니다.
4. historical reasoning이 필요하면 `docs/archive/2026-q1/BRANCH_MAIN_GAP_ANALYSIS.md`를 참고합니다.

## 1) 상태 스냅샷

- 기준 날짜: 2026년 3월 9일
- 로컬/원격 상태: `main`이 존재하고 `origin/main`과 동기화 가능
- `release/*` 로컬/원격 브랜치: 현재 없음
- open RR 이슈 정리 결과: release/refactor 관련 stale RR는 모두 닫혔고, 남은 open follow-up은 `#209` 하나입니다.

## 2) release 스트림 상태

| 스트림 | 현재 상태 | 근거 | 결론 |
|---|---|---|---|
| `release/ci-platform` | 별도 branch 통합 불필요 | CI/policy/preflight 관련 변경이 이미 `main`에 직접 반영됨. manifest는 유지하되 경로는 현재 구조로 보정함. | `merged / superseded as separate release branch` |
| `release/runtime-binary-bootstrap` | 별도 branch 통합 불필요 | `web/runtime_paths.py`, `web/app.py`, runtime bootstrap 관련 파일이 이미 `main`에 존재 | `merged / keep as reference manifest` |
| `release/runtime-binary` | 기반 작업은 main 반영, 전용 release 실행은 미계획 | Windows artifact/signing 관련 스크립트와 문서가 `main`에 존재하고 기존 RR도 완료됨. 다만 현재 `main` 기준 실제 Windows release dry-run은 별도 업무로 다시 열어야 함 | `partially actionable only when a Windows release is scheduled` |
| `release/scheduler-reliability` | 별도 branch 통합 불필요 | `schedule_runner`, `shutdown_manager`, 관련 테스트/게이트가 이미 `main`에 직접 반영됨 | `merged / superseded as separate release branch` |

## 3) manifest 상태

### `release-ci-platform`

- 현재도 참고용 manifest로 유지합니다.
- 2026년 3월 9일 기준으로 죽은 경로 2개를 현재 경로로 보정했습니다.
  - `LOCAL_CI_GUIDE.md` -> `docs/dev/LOCAL_CI_GUIDE.md`
  - `check_quality.py` -> `scripts/devtools/check_quality.py`

### `release-runtime-binary-bootstrap`

- 모든 manifest 경로가 현재 `main`에서 유효합니다.
- 다만 이 manifest는 "과거 분리 통합 계획의 참고 기준"이지 즉시 branch cut 지시서는 아닙니다.

### `release-runtime-binary`

- manifest 경로는 현재도 모두 유효합니다.
- 실제 release 대상으로 다시 사용할 경우, 현재 `main` 기준 Windows signing/release dry-run RR를 새로 열어 재검증해야 합니다.

### `release-scheduler-reliability`

- manifest 경로는 현재도 모두 유효합니다.
- 별도 release branch 계획은 종료하고, 이후 scheduler work는 일반 RR 흐름으로 다룹니다.

## 4) issue 정리 결과

2026년 3월 9일에 다음 stale RR 이슈를 실제 merged PR 기준으로 닫았습니다.

- repo/release hygiene: `#106 #108 #110 #112 #114 #116 #118 #137 #138 #140`
- runtime/config/web refactor: `#179 #182 #205 #206 #210 #212 #220 #221 #223 #224 #225 #226 #227 #228 #229`
- product follow-up already delivered: `#195 #197`

현재 release/ops 후속으로 열려 있는 것은 아래 하나뿐입니다.

- `#209` Follow-up: phase 2 operational security hardening

## 5) 지금부터의 실행 원칙

1. release 관련 새 작업은 과거 RR 재사용 없이 새 RR로 엽니다.
2. branch를 만든다면 출발점은 항상 **현재 `main`** 입니다.
3. 새 release RR는 아래 세 조건을 모두 만족할 때만 엽니다.
   - 현재 `main`에 아직 없는 결과물이 명확함
   - manifest가 현재 경로 기준으로 유효함
   - `make preflight-release`, `make check`, `make check-full` 실행 계획이 먼저 정의됨

## 6) 바로 남은 일

### A. 지금 즉시 할 일

- release branch를 추가로 만들 필요는 없습니다.
- release 문서의 실행 기준은 이 문서로 단일화합니다.

### B. 다음에 새 RR로 열 수 있는 일

1. Windows binary release dry-run from current `main`
   - 조건: 실제 Windows release를 다시 추진할 때만
   - 방식: 현재 `main`에서 새 RR 생성 후 signing/dry-run 증적을 다시 수집
2. `#209` phase 2 operational security hardening
   - stronger auth
   - centralized/distributed throttling
   - quota/abuse policy

## 7) future release branch가 정말 필요할 때의 최소 절차

```bash
# always cut from current main, not from baseline/main-equivalent
git checkout main
git pull --ff-only origin main
git checkout -b release/<topic>

make preflight-release
make check
make check-full
```

- PR 템플릿: `.github/PULL_REQUEST_TEMPLATE/release_integration.md`
- 메타데이터 적용: `make apply-pr-metadata PR=<number>`
- 머지 방식: 기본 squash merge

## 8) 결론

release 통합 계획의 핵심은 더 이상 "예전 baseline에서 branch를 다시 자르는 것"이 아닙니다.
현재 기준으로는 대부분의 release stream이 이미 `main`에 흡수되었고, 남은 실질 후속은
`Windows release를 다시 실제로 추진할지 여부`와 `#209 보안 hardening`뿐입니다.
