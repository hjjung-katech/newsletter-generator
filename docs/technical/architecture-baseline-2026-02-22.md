# Architecture Baseline (2026-02-22)

## Snapshot Scope
- Repository: `newsletter-generator-codex-skills-agents`
- Date: 2026-02-22
- Branch: `codex/docs-refactor-pra-20260221`

## Import Direction Snapshot
- `web -> newsletter`: 13 occurrences
- `newsletter -> web`: 0 occurrences
- import cycle (SCC>1): 0

## Churn Snapshot (12 months)
Top folders by touched-file frequency:
- `newsletter`: 318
- `tests`: 285
- `web`: 78
- `docs`: 73

Top files by touched-file frequency:
- `newsletter/chains.py`: 37
- `newsletter/cli.py`: 35
- `newsletter/tools.py`: 30
- `newsletter/graph.py`: 26
- `newsletter/compose.py`: 24
- `web/app.py`: 16

## Guardrail Baseline
- Rule source: `scripts/architecture/boundary_rules.yml`
- Ratchet baseline: `scripts/architecture/boundary_baseline.json`
- Expected behavior:
  - 신규 위반/확대 위반: fail
  - 기존 위반 감소: pass

## Notes
- 본 baseline은 구조 리팩토링 전 고정 지점입니다.
- 이후 baseline은 "위반 감소"인 경우에만 업데이트합니다.
