# Main 통합 실행 계획 (즉시 실행 버전)

본 문서는 `docs/dev/BRANCH_MAIN_GAP_ANALYSIS.md`의 전략을 실제 실행 순서로 옮긴 플레이북입니다.

## 0) 실패 재발 방지 원칙 (필수)

1. 기준선 고정: `baseline/main-equivalent` 태그에서만 release 브랜치 시작
2. 범위 고정: 릴리즈별 manifest(포함 파일 목록) 기반 반영
3. 환경 고정: `make preflight-release` 통과 전 테스트/PR 진행 금지
4. 메타데이터 고정: PR 본문 기재 + GitHub 라벨/리뷰어 실제 적용

## 1) 통합 순서

1. `release/ci-platform`
2. `release/runtime-binary`
3. `release/scheduler-reliability`

각 단계는 이전 단계가 `main`에 머지되고 24시간 관측 윈도우를 통과한 뒤 진행합니다.

## 2) 브랜치 생성/동기화

```bash
# baseline 태그가 없으면 1회 생성 (예: 워크플로우 통합 기준 커밋)
git tag baseline/main-equivalent 1e93460
```

```bash
# baseline 태그를 기준으로 시작
git checkout -b release/ci-platform baseline/main-equivalent
git checkout -b release/runtime-binary baseline/main-equivalent
git checkout -b release/scheduler-reliability baseline/main-equivalent
```

## 3) PR 생성 전 공통 체크

```bash
# 사전 점검 (필수)
make preflight-release

# quick gate
make test-quick

# full gate
make test-full

# scheduler/runtime 고위험 변경 시
make test-nightly
```

- PR 템플릿: `.github/PULL_REQUEST_TEMPLATE/release_integration.md`
- 리뷰어: 코드 오너 + 운영 담당
- 머지 방식: 기본 squash merge (필요 시 merge commit)

## 4) release/ci-platform 반영 방식 (manifest)

- 원칙: 커밋 단위 선별보다 파일 목록 선별을 우선
- 예시 명령:

```bash
# 포함 파일 목록을 확인 후 work에서 가져오기
git restore --source=work -- \
  .github/workflows/ \
  .pre-commit-config.yaml \
  .githooks/pre-push \
  run_ci_checks.py \
  check_quality.py \
  Makefile \
  LOCAL_CI_GUIDE.md

# 범위 검증 (manifest 외 파일 유입 방지)
make validate-ci-manifest
```

## 5) 머지 후 운영

1. 태그 발행 (`vX.Y.Z`)
2. `CHANGELOG.md` 업데이트
3. 24시간 KPI 관측
   - CI First Pass Rate
   - 스케줄 누락/중복
   - 비정상 종료율
4. 이상 징후 시 태그 기준 즉시 롤백

## 6) 이번 주 시작 작업(착수)

- [x] PR 템플릿 추가
- [x] quick/full/nightly 실행 타겟 정리 (`Makefile`)
- [x] preflight 스크립트 추가 (`scripts/release_preflight.py`)
- [ ] `release/ci-platform` 브랜치 분리 및 PR 생성
- [ ] `release/runtime-binary` 브랜치 분리 및 PR 생성
- [ ] `release/scheduler-reliability` 브랜치 분리 및 PR 생성


## 7) PR 메타데이터 실제 적용(자동화)

본문 체크리스트만으로는 라벨/리뷰어가 반영되지 않으므로, PR 생성 직후 아래를 실행합니다.

```bash
make apply-pr-metadata PR=<number> REVIEWERS=<code_owner,ops_owner>
```

- 기본 라벨: `release`, `risk:medium`, `area:ci`
- 리뷰어는 GitHub handle을 쉼표로 전달
