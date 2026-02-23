# PR Process Template (CI Unit)

## Summary
- What changed and why.

## Scope (in/out)
### In scope
-

### Out of scope
-

## Branch / Commit
- Branch: `codex/<topic>`
- Commits in this PR:
  - `<hash> <summary>`

## Test Evidence
- [ ] `make check` passed
- [ ] `make check-full` passed
- [ ] `make repo-audit` executed (for structure/policy/docs changes)

### Commands run
```bash
make check
make check-full
make repo-audit
```

## CI Status (GitHub Actions)
- Main CI Pipeline: `<url or pass/fail>`
- Docs Quality: `<url or pass/fail>`
- Other relevant workflows: `<url or pass/fail>`

## Risk / Rollback
- Primary risk:
- Rollback plan:
  1. Revert commit(s) from this PR.
  2. Re-run verification gates.
- Recovery verification:
  - `make check`
  - `make check-full`

## Agent / Skill Used
- [ ] Repo Hygiene Agent (A)
- [ ] Ops Safety Agent (B)
- [ ] Docs SSOT Agent (C)
- [ ] Release Guard Agent (D)
- [ ] `$gh-fix-ci`
- [ ] `$gh-address-comments`
- [ ] Not used (reason):
