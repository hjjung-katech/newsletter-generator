# Agent/Skill Request Playbook

This document standardizes work as `RR -> Branch -> Commit -> PR -> CI -> Merge`.

## Purpose

- Manage work as clear PR-sized delivery units.
- Split CI failure handling and review-comment handling into dedicated skills.
- Standardize request wording so long-running work stays reproducible.

## Basic Execution Contract

Include the following nine requirements in the request by default.

1. Create an RR (Review Request) first: `.github/ISSUE_TEMPLATE/review-request.yml`
2. Require a `Delivery Unit ID` in the RR, and keep a strict 1:1 mapping between RR and PR
3. Use the branch pattern `<type>/<scope>-<topic>` such as `codex/workflow-template-standard`
4. Use `.gitmessage.txt` as the commit-message template and split commits by meaning
5. Keep commit count in the default `1-6` range (exempt labels: `docs-only`, `trivial`, `hotfix`)
6. Run local gates: `make check`, `make check-full`, and `make repo-audit` when needed
7. Include the `## Delivery Unit` section in `.github/pull_request_template.md`
8. Check GitHub Actions results and report status
9. When a check fails, classify the cause and add a follow-up fix commit; avoid force-push unless there is a strong reason

## Enforcement Principles

- Codex/agents follow the repository root `AGENTS.md` first.
- Use CI policy checks so the same governance applies to human contributors.
- CI enforcement: `.github/workflows/pr-policy-check.yml`
- Delivery Unit validator: `scripts/ci/validate_delivery_unit.py`
- RR auto-close after merge: `.github/workflows/rr-lifecycle-close.yml` (parses `RR: #<n>`)

## Standard Template Locations

- RR template: `.github/ISSUE_TEMPLATE/review-request.yml`
- Commit template: `.gitmessage.txt`
- PR template: `.github/pull_request_template.md`
- Consolidated workflow guide: `docs/dev/WORKFLOW_TEMPLATES.md`
- Delivery Unit check: `scripts/ci/validate_delivery_unit.py`

Set the local commit template once:

```bash
git config commit.template .gitmessage.txt
```

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

### 1) Structure improvement request

```text
Handle this as a PR-sized unit of work.
- Goal: <goal>
- Scope: <in-scope / out-of-scope>
- Branch: <type>/<scope>-<topic>
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

## PR Completion Report

Use this format when work is complete.

1. Commit list (hash + summary)
2. PR link
3. Local validation results (`make check`, `make check-full`, and any extras)
4. GitHub Actions status (success/failure, and the failure cause if applicable)
5. Risk and rollback note
