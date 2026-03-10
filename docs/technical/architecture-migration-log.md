# Architecture Migration Log

이 문서는 active migration 사실만 기록합니다.
현재 저장소에 존재하지 않는 경로나 채택되지 않은 실험안은 future checkpoint로 남기지 않습니다.

## 2026-02-22

### Completed

- Added architecture guardrails:
  - `scripts/architecture/check_import_boundaries.py`
  - `scripts/architecture/check_import_cycles.py`
  - `scripts/architecture/boundary_rules.yml`
  - `scripts/architecture/boundary_baseline.json`
- Wired guardrails into:
  - `run_ci_checks.py`
  - `.github/workflows/main-ci.yml`
  - `Makefile` (`architecture-check`, `architecture-baseline`)
- Introduced `newsletter_core/{public,application,domain,infrastructure,internal}` as the gradual migration target.
- Migrated the first generation slice behind `newsletter_core.public` facade.
- Switched active runtime paths to consume `newsletter_core.public.generation`.
- Added contract coverage for public facade and web/runtime behavior.

### Historical correction

- 초기 구조 이행 과정에서 wrapper-style runtime experiment가 있었지만 현재 active 구조로 유지되지는 않았습니다.
- 현재 저장소에서 `apps/` 는 `apps/experimental/` 만 유지합니다.
- contributor-facing run surface의 정본은 `python -m scripts.devtools.dev_entrypoint` 입니다.

## 2026-03-10

### Current active state

- `newsletter_core/` 는 신규 기능과 점진적 구조 이동의 목표 영역으로 유지합니다.
- `newsletter/` 는 legacy surface manifest와 ADR guardrail 아래에서 고정하며, 신규 Python 모듈 유입을 허용하지 않습니다.
- web runtime은 `newsletter_core.public.generation` 경유 계약을 유지합니다.
- 현재 구조 부채의 중심은 root cleanup이 아니라 legacy hotspot 축소입니다.

### Active burn-down targets

- `web/routes_generation.py`
- `newsletter/tools.py`
- `newsletter/llm_factory.py`
- `newsletter/graph.py`
- `web/static/js/app.js`

### Next checkpoints

1. hotspot reduction은 small-batch extraction으로만 진행합니다.
2. extraction 전에 contract / ops-safety suite를 먼저 고정합니다.
3. `newsletter/` 확장이 아니라 `newsletter_core/` 경계 강화가 다음 구조 목표입니다.
4. 현재 runtime entrypoint, support policy, CI contract는 변경하지 않습니다.

### Current validation commands

- `python3 scripts/repo_audit.py --policy scripts/repo_hygiene_policy.json --output-dir .local/artifacts/repo-audit --check-policy --strict`
- `make check`
- `python -m scripts.devtools.dev_entrypoint check --full`
