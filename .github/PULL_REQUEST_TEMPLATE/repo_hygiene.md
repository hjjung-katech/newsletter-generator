# Repo Hygiene Pull Request

## Summary (what / why)
-

## Scope
### In Scope
-

### Out of Scope
-

## Branch / Commit
- Branch: `<type>/<scope>-<topic>`
- Commit template: `.gitmessage.txt`
- Commits in this PR:
  - `<hash> <summary>`

## Delivery Unit
RR: #<n>
Delivery Unit ID:
Merge Boundary:
Rollback Boundary:

## Test & Evidence
- [ ] `make check`
- [ ] `make check-full`
- [ ] `make repo-audit` (for structure/policy changes)

### Commands and Results
```bash
make check
make check-full
make repo-audit
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

## Agent / Skill Used
- [ ] Repo Hygiene Agent (A)
- [ ] Docs SSOT Agent (C)
- [ ] `$gh-fix-ci`
- [ ] `$gh-address-comments`
