# Release Integration Pull Request

## Summary (what / why)
-

## Base
- Base branch/tag: (e.g. `main` or `baseline/main-equivalent`)
- Base commit SHA:

## Scope
### In Scope
-

### Out of Scope
-

## Delivery Unit
RR: #<n>
Delivery Unit ID:
Merge Boundary:
Rollback Boundary:

## Test & Evidence
- [ ] `make check`
- [ ] `make check-full`
- [ ] `make preflight-release`
- [ ] release manifest validation completed

### Commands and Results
```bash
make preflight-release
make check-full
make validate-ci-manifest
```

## Risk & Rollback
- Risk:
- Rollback:

## Ops-Safety Addendum (if touching protected paths)
- Idempotency key 생성/적용 범위:
- Outbox/send_key 중복 방지 결과:
- import-time side effect 제거 여부:

## Not Run (with reason)
-

## Release Notes Checklist
- [ ] CHANGELOG updated
- [ ] Docs updated (or reason documented)
- [ ] Required CI checks passed before merge
