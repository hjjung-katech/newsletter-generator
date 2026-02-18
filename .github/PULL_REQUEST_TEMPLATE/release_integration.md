## Summary
- What changed in this release branch and why.

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
- [ ] format/lint passed
- [ ] core unit tests passed
- [ ] schedule/shutdown integration tests passed
- [ ] security scan completed (new high issues = 0)

### Commands run
```bash
make test-quick
make test-full
# For scheduler/runtime-risk changes only
make test-nightly
```

## Rollback Plan
- Tag to rollback to:
- Rollback command / process:
- Data migration impact (if any):

## Docs Updated
- [ ] CHANGELOG updated
- [ ] Related docs updated
- [ ] No docs change needed (reason):
