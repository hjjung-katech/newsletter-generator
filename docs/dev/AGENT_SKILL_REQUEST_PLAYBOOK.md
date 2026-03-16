# Agent/Skill Request Playbook

This document complements the canonical workflow in `docs/dev/CI_CD_GUIDE.md`.
Use it when you need skill-specific request wording rather than the base RR/PR process.

## Purpose

- Route specialized requests to the right skill or agent.
- Keep CI failure handling and review-comment handling distinct from general RR execution.
- Reuse concise request patterns without duplicating the full workflow standard.

## Canonical Workflow Boundary

- RR/branch/commit/PR/merge 운영 표준은 `docs/dev/CI_CD_GUIDE.md` 가 정본입니다.
- `AGENTS.md` 와 `docs/dev/AGENTS_GOVERNANCE.md` 는 agent policy precedence를 다룹니다.
- 이 문서는 위 정본을 대체하지 않고, skill 사용 시의 요청 문장 예시만 제공합니다.

## Skill Selection

| Situation | Recommended Skill/Agent | How to use it |
|---|---|---|
| Analyze or fix failing GitHub Actions checks on the current PR | `$gh-fix-ci` | Collect failure logs -> summarize root cause -> propose a fix plan -> implement after approval |
| Address review comments on the open PR for the current branch | `$gh-address-comments` | Collect comments -> confirm selected items -> apply only the selected fixes |
| Execute structure/policy cleanup work | Repo Hygiene Agent (A) | `repo_audit` + policy docs + small-batch PRs |
| Reconcile docs and source-of-truth config | Docs SSOT Agent (C) | Update the canonical document first, then run link/style checks |
| Work on operational safety concerns | Ops Safety Agent (B) | Check idempotency, outbox behavior, and config regression risks |
| Run pre-release integration checks | Release Guard Agent (D) | Run preflight, manifest validation, and release-template checks |

## Request Templates

### 1) PR-sized structure improvement request

```text
Handle this as a PR-sized unit of work.
- Delivery mode: rr-branch-commit-pr
- RR Reference: #<n>
- Goal: <goal>
- Scope: <in-scope / out-of-scope>
- Branch: <type>/<scope>-<topic>
- Base branch: <base-branch>
- First output must begin with [DELIVERY_CHECK]
- Required gates: make check, make check-full, make repo-audit
- Deliverables: commit hashes, PR link, CI status, rollback note
- Working style: small-batch (target <=300 LOC and <=8 files per PR when practical)
```

### 2) CI failure response request

```text
Use $gh-fix-ci to inspect the failing checks on the current PR.
Summarize the root cause and proposed fix plan first, then implement after approval.
```

### 3) Review-comment response request

```text
Use $gh-address-comments to collect PR comments for the current branch.
List the comment items first, then apply only the ones I select.
```

## Output Reminder

When a skill-assisted task completes, report:

1. commit hash or commit list
2. PR link
3. local validation results
4. GitHub Actions status
5. risk and rollback note
