# Repo Hygiene / CI-managed PR

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
- [ ] `make repo-audit` executed (for structure/policy changes)

### Commands run
```bash
make check
make check-full
make repo-audit
```

## CI Status (GitHub Actions)
- Main CI: `<url or pass/fail>`
- Docs Quality: `<url or pass/fail>`
- Other relevant workflows: `<url or pass/fail>`

## Risk / Rollback
- Primary risk:
- Rollback plan:
  - Revert commit(s):
  - Recovery verification command:

## Agent/Skill Used
- [ ] Repo Hygiene Agent(A)
- [ ] Docs SSOT Agent(C)
- [ ] `$gh-fix-ci`
- [ ] `$gh-address-comments`
- [ ] Not used (reason):
