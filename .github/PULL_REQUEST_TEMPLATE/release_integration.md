## Summary
- What changed in this release branch and why.

## Base
- Base branch/tag: (e.g. `main` or `baseline/main-equivalent`)
- Base commit SHA:

## Scope (in/out)
### In scope
- 

### Out of scope
- 

## Risk
- Primary runtime/operational risks.
- Affected high-risk files (if any):
  - [ ] `web/app.py`
  - [ ] `web/schedule_runner.py`
  - [ ] `web/graceful_shutdown.py`
  - [ ] `newsletter/utils/shutdown_manager.py`

## Test Evidence
- [ ] preflight passed
- [ ] format/lint passed
- [ ] core unit tests passed
- [ ] schedule/shutdown integration tests passed
- [ ] security scan completed (new high issues = 0)

### Commands run
```bash
make preflight-release
make test-quick
make test-full
# release/ci-platform 범위 검증
make validate-ci-manifest
# PR 메타데이터 실제 적용
make apply-pr-metadata PR=<number> REVIEWERS=<owner1,ops1>
# For scheduler/runtime-risk changes only
make test-nightly
```

## PR Metadata Applied
- [ ] Labels applied in GitHub UI/API (`release`, `risk:*`, `area:*`)
- [ ] Reviewers assigned in GitHub UI/API (code owner + ops owner)

## Rollback Plan
- Tag to rollback to:
- Rollback command / process:
- Data migration impact (if any):

## Docs Updated
- [ ] CHANGELOG updated
- [ ] Related docs updated
- [ ] No docs change needed (reason):
