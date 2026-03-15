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

## 2026-03-14

### Close-out state

- docs truth alignment, repo hygiene hard gate, legacy burn-down, schedule/history visibility, approval visibility, preset visibility, source policy visibility, personalization visibility, settings provenance/diagnostics 까지를 현재 baseline으로 고정합니다.
- 추가 구조 분해를 기본 전략으로 두지 않고, hotspot shell을 maintenance mode 대상으로 전환합니다.

### Maintenance mode targets

- `newsletter/llm_factory.py`
- `newsletter/tools.py`
- `newsletter/graph.py`
- `web/routes_generation.py`
- `web/static/js/app.js`

### Reopen conditions

1. user-facing bug fix 또는 incident 대응 중 동일 영역 수정이 직접 필요할 때
2. 새로운 제품 요구가 해당 shell 변경을 직접 요구할 때
3. 중복 로직이 재유입되어 maintenance cost가 다시 커질 때
4. shell LOC 또는 complexity가 다시 유의미하게 증가할 때

### Optional backlog

- richer mismatch diagnostics
- deeper provenance lineage
- time-based settings/result drill-down

### Current validation commands

- `python3 scripts/repo_audit.py --policy scripts/repo_hygiene_policy.json --output-dir .local/artifacts/repo-audit --check-policy --strict`
- `make check`
- `make check-full`

## 2026-03-15

### Strategy close-out declaration

- 전략 실행은 공식 close-out 상태로 전환합니다.
- 현재 baseline은 docs truth alignment, repo hygiene hard gate, legacy burn-down, schedule/history visibility, approval visibility, preset visibility, source policy visibility, personalization visibility, settings provenance/diagnostics, field-level mismatch explanation, lineage summary/detail 까지 포함합니다.
- 이후 기본 운영 원칙은 "추가 구조 분해"가 아니라 maintenance mode 유지와 예외적 reopen 만 허용하는 방식입니다.

### Maintenance mode targets

- `newsletter/llm_factory.py`
- `newsletter/tools.py`
- `newsletter/graph.py`
- `web/routes_generation.py`
- `web/static/js/app.js`

### Reopen conditions

1. user-facing bug fix 또는 incident 대응 중 동일 영역 수정이 직접 필요할 때
2. 새로운 제품 요구가 해당 shell 변경을 직접 요구할 때
3. 중복 로직이 재유입되어 maintenance cost가 다시 커질 때
4. shell LOC 또는 complexity가 다시 유의미하게 증가할 때
5. 반복된 운영 해석 요청이 optional backlog 범위를 정당화할 때

### Optional backlog

- richer causal mismatch diagnostics
- deeper provenance lineage history
- time-based settings/result drill-down
- deeper causal explanation

### Current validation commands

- `python3 scripts/repo_audit.py --policy scripts/repo_hygiene_policy.json --output-dir .local/artifacts/repo-audit --check-policy --strict`
- `make check`
- `make check-full`
- `.local/venv/bin/python scripts/check_markdown_links.py`
- `.local/venv/bin/python scripts/check_markdown_style.py docs/ARCHITECTURE.md docs/dev/LONG_TERM_REPO_STRATEGY.md`
