# Codex Instruction Layout

Purpose: keep instructions enforceable, not bloated.

## Load/Override Order
1. `~/.codex/AGENTS.md` (global working style)
2. `repo-root/AGENTS.md` (repository-specific policy)
3. deeper `AGENTS.md` (for example `web/AGENTS.md`) when working in that subtree

If rules conflict, the deeper/later file wins for that scope.

## What Goes Where
- Global (`~/.codex/AGENTS.md`): planning discipline, verification evidence format, safety baseline, bug-fix workflow.
- Repo (`AGENTS.md`): runtime stack choices, canonical env vars, required gates, must-follow web guardrails, ops-safety locks/reporting, RR/PR contract.
- Subdir (`web/AGENTS.md`): web-runtime detail and stricter guidance for work performed from that subtree.

## Skills vs AGENTS
Use `AGENTS.md` for concise policy. Use skills for repeatable procedures.
Do not move must-follow safety rules or required reporting entirely into skills.

Current repo skills live under `.agents/skills/`:
- `ci-gate`
- `scheduler-debug`
- `web-smoke`
- `docs-and-config-consistency`
- `release-integration`

Add a new skill when a procedure is repeated often or has fragile steps.
Keep skill detail in `SKILL.md`; keep AGENTS policy-level only.

## Change Control
- Update global and repo rules separately; avoid copy/paste duplication.
- Keep each AGENTS file short enough to scan in under 2 minutes.
- If a rule is temporary, document owner + removal condition in the PR.
