# Main 통합 실행 계획 (즉시 실행 버전)

본 문서는 `docs/dev/BRANCH_MAIN_GAP_ANALYSIS.md`의 전략을 실제 실행 순서로 옮긴 플레이북입니다.

## 1) 통합 순서

1. `release/ci-platform`
2. `release/runtime-binary`
3. `release/scheduler-reliability`

각 단계는 이전 단계가 `main`에 머지되고 24시간 관측 윈도우를 통과한 뒤 진행합니다.

## 2) 브랜치 생성/동기화

```bash
git checkout main
git pull --ff-only origin main

# 1차
 git checkout -b release/ci-platform

# 2차
 git checkout main
 git checkout -b release/runtime-binary

# 3차
 git checkout main
 git checkout -b release/scheduler-reliability
```

## 3) PR 생성 전 공통 체크

```bash
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

## 4) 머지 후 운영

1. 태그 발행 (`vX.Y.Z`)
2. `CHANGELOG.md` 업데이트
3. 24시간 KPI 관측
   - CI First Pass Rate
   - 스케줄 누락/중복
   - 비정상 종료율
4. 이상 징후 시 태그 기준 즉시 롤백

## 5) 이번 주 시작 작업(착수)

- [x] PR 템플릿 추가
- [x] quick/full/nightly 실행 타겟 정리 (`Makefile`)
- [ ] `release/ci-platform` 브랜치 분리 및 PR 생성
- [ ] `release/runtime-binary` 브랜치 분리 및 PR 생성
- [ ] `release/scheduler-reliability` 브랜치 분리 및 PR 생성
