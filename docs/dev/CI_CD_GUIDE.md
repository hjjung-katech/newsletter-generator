# CI/CD Guide

## Overview

이 문서는 현재 운영 중인 CI/CD 파이프라인의 정본 가이드입니다.
지원 정책 정본은 `../reference/support-policy.md`를 기준으로 유지합니다.

## Active GitHub Actions Workflows

현재 운영 워크플로우는 아래 7개입니다.

1. `main-ci.yml`
- 코드 품질, 테스트, 빌드 검증
- 주요 브랜치 push/PR에서 실행
- PR 정책 검증은 별도 `pr-policy-check.yml`에서 수행

2. `deployment.yml`
- 배포 파이프라인 (Railway + Pages 병행)
- `main` push, 스케줄, 수동 실행

3. `security-scan.yml`
- 정기 보안 스캔
- 스케줄/수동 실행

4. `docs-quality.yml`
- Markdown 링크/스타일 품질 검증
- 문서 변경 push/PR에서 실행

5. `ops-safety-monitor.yml`
- 운영 안전성 모니터링(정기/수동)
- 스케줄/수동 실행

6. `pr-policy-check.yml`
- PR 정책 검증(브랜치명/템플릿/커밋 메시지)
- PR 이벤트(opened/edited/synchronize/reopened)에서 실행

7. `rr-lifecycle-close.yml`
- 머지된 PR 본문의 `RR: #<n>`를 기준으로 RR 이슈 자동 종료
- PR closed(merged only) 이벤트에서 실행

## Current Verification Truth

- PR gate:
  - Linux: Ubuntu `unit-tests`(py3.11/3.12), `Release Preflight`, `Source Smoke (ubuntu-latest)`, `Build Check (ubuntu-latest)`, `Container Smoke (ubuntu-latest)`, `Mock API Tests`
  - Windows: `Source Smoke (windows-latest)`, `Build Check (windows-latest)`
  - macOS: `Source Smoke (macos-latest)`
- long gate (`push` to `main`/`develop`/`release/**`):
  - Linux: PR gate + `Integration Tests`
  - Windows: PR gate + `Windows Burn-in Gate (main)` on `main` push
- Linux container smoke는 canonical packaging target을 실제로 검증하지만, promoted Docker image publish lane 자체를 의미하지는 않습니다.
- Windows source smoke + runtime subset은 EXE build-check를 대체하지 않고, source development 1차 지원 계약을 별도 집행합니다.
- macOS source smoke + runtime subset은 source-based development/smoke 중심의 2차 지원 계약만 집행합니다.

## Local Gate Commands

표준 로컬 게이트의 정본은 Python entrypoint이며, Makefile은 backward-compatible wrapper로 유지합니다.

```bash
cd newsletter-generator
python -m scripts.devtools.dev_entrypoint bootstrap
python -m scripts.devtools.dev_entrypoint doctor
python -m scripts.devtools.dev_entrypoint check
python -m scripts.devtools.dev_entrypoint check --full
python -m scripts.devtools.dev_entrypoint smoke web
make repo-audit
make repo-audit-strict
```

- `python -m scripts.devtools.dev_entrypoint check`: 빠른 로컬 게이트
- `python -m scripts.devtools.dev_entrypoint check --full`: PR 전 전체 게이트
- `python -m scripts.devtools.dev_entrypoint smoke web`: cross-platform source web smoke
- `make repo-audit`: 루트 인벤토리 + repo hygiene soft gate 리포트 생성
- `make repo-audit-strict`: CI hard gate와 동일(strict) 경로 점검
- dev 유틸 실행 스크립트는 `scripts/devtools/`를 기본 경로로 사용합니다.
- `make bootstrap`, `make doctor`, `make check`, `make check-full`는 같은 Python 엔트리포인트를 호출합니다.

## Quality Toolchain

현재 품질 게이트는 아래 도구 조합을 기준으로 운영합니다.

| Area | Primary Tool | Canonical Entry |
|---|---|---|
| formatting | `black` | `python -m scripts.devtools.dev_entrypoint check`, `python -m scripts.devtools.dev_entrypoint check --full`, `make format` |
| import ordering | `isort` | `python -m scripts.devtools.dev_entrypoint check`, `python -m scripts.devtools.dev_entrypoint check --full`, `make format` |
| lint | `flake8` | `python -m scripts.devtools.dev_entrypoint check`, `python -m scripts.devtools.dev_entrypoint check --full` |
| type check | `mypy` | `python -m scripts.devtools.dev_entrypoint check --full` |
| security scan | `bandit` | `python -m scripts.devtools.dev_entrypoint check --full` |
| unit/integration test | `pytest` | `python -m scripts.devtools.dev_entrypoint check`, `python -m scripts.devtools.dev_entrypoint check --full` |
| docs integrity | Markdown link/style checks | `make docs-check` |
| repo hygiene | `scripts/repo_audit.py` | `make repo-audit`, `make repo-audit-strict` |

직접 도구를 개별 실행할 수도 있지만, contributor-facing 기준 명령은 `python -m scripts.devtools.dev_entrypoint ...` 입니다.

## Coverage Reporting

- 커버리지는 `pytest-cov` 리포트(`.local/coverage/coverage.xml`, `.local/coverage/htmlcov/`)로 계속 수집합니다.
- 현재 contributor gate는 "고정 퍼센트 임계치" 문서보다 `python -m scripts.devtools.dev_entrypoint check --full` 통과와 테스트 리포트 정합성을 우선 기준으로 사용합니다.
- 커버리지 개선 작업은 별도 RR/PR 단위로 분리합니다.
- repo audit, coverage, debug 같은 로컬 scratch 산출물은 기본적으로 루트 `.local/` 아래에 격리합니다.

## CI Gate Split

### PR Gate

아래 12개 check는 `main` branch protection required check 기준이다.

- `policy-check`
- `docs-quality`
- `Code Quality & Security`
- `Unit Tests - ubuntu-latest-py3.11`
- `Unit Tests - ubuntu-latest-py3.12`
- `Release Preflight`
- `Source Smoke (ubuntu-latest)`
- `Source Smoke (macos-latest)`
- `Source Smoke (windows-latest)`
- `Build Check (ubuntu-latest)`
- `Build Check (windows-latest)`
- `Container Smoke (ubuntu-latest)`

추가 PR validation:
- `Mock API Tests`
  - PR에서 계속 실행하지만 현재 branch protection required check에는 포함하지 않는다.

### Long Gate

- `Integration Tests`
  - `push` to `main`/`develop`에서만 실행합니다.
- `Windows Burn-in Gate (main)`
  - `main` push에서만 실행합니다.

PR gate는 빠르고 결정적인 계약 검증에 집중하고, long gate는 장시간 시나리오와 main branch burn-in을 맡습니다.

## Repo Hygiene Gate

`main-ci.yml`의 `quality-checks` 단계에서 repo hygiene gate를 실행합니다.

```bash
python scripts/repo_audit.py \
  --policy scripts/repo_hygiene_policy.json \
  --output-dir .local/artifacts/repo-audit \
  --check-policy
```

- 현재 기본 운영: `REPO_HYGIENE_STRICT=true` (hard gate)
- 임시 예외 경로: `REPO_HYGIENE_STRICT=false`로 soft gate override 가능(권장하지 않음)
- CI artifact:
  - `.local/artifacts/repo-audit/repo_audit_report.md`
  - `.local/artifacts/repo-audit/repo_audit_report.json`
  - `.local/artifacts/repo-audit/policy_warnings.md`

## PR Policy Check Gate

`.github/workflows/pr-policy-check.yml`에서 아래를 검사합니다.

1. 브랜치명 정책
- 형식: `<type>/<scope>-<topic>`
- 허용 타입: `feat|fix|chore|docs|refactor|release|codex`

2. PR 본문 필수 섹션
- `## Summary (what / why)`
- `## Scope`
- `## Test & Evidence`
- `## Risk & Rollback`
- `## Ops-Safety Addendum (if touching protected paths)`
- `## Not Run (with reason)`

3. 커밋 메시지 첫 줄 규칙
- 형식: `<type>(<scope>): <summary>`
- summary 최대 72자

## Contributor Workflow Standard

기여자 workflow 정본은 이 섹션을 기준으로 유지합니다.

1. RR 생성
- GitHub RR 템플릿: `.github/ISSUE_TEMPLATE/review-request.yml`
- RR 1건은 기본적으로 PR 1건과 1:1로 대응합니다.
- `Delivery Unit ID` 를 RR과 PR 모두에 유지합니다.

2. 브랜치 네이밍
- 기본 패턴: `<type>/<scope>-<topic>`
- 허용 type: `feat|fix|chore|docs|refactor|release|codex`

3. 커밋 메시지
- 기본 패턴: `<type>(<scope>): <summary>`
- summary는 72자 이하, 명령형, 마침표 없이 작성합니다.
- 기본 커밋 수는 PR당 `1-6` 범위를 권장합니다.

4. PR 본문
- `.github/pull_request_template.md` 의 필수 섹션을 모두 채웁니다.
- `## Delivery Unit` 섹션에 `RR`, `Delivery Unit ID`, merge/rollback boundary를 명시합니다.

5. Merge 정책
- 기본 merge 방식: squash merge
- merge 전 조건: `python -m scripts.devtools.dev_entrypoint check --full` 및 GitHub required checks green
- hotfix 등 예외는 `## Not Run` 에 사유를 남깁니다.

## Request Entry Patterns

### Standard RR request

```text
이번 작업은 PR 단위로 끝까지 진행해줘.
- 목표: <목표>
- 범위: <in-scope / out-of-scope>
- 브랜치: <type>/<scope>-<topic>
- 필수 게이트: `python -m scripts.devtools.dev_entrypoint check`, `python -m scripts.devtools.dev_entrypoint check --full`
- 선택 게이트: make repo-audit (구조/정책 변경 시)
- 산출물: 커밋 해시, PR 링크, CI 상태, merge 결과, 롤백 메모
```

### CI failure request

```text
Use $gh-fix-ci to inspect the failing checks on the current PR.
Summarize the root cause and proposed fix plan first, then implement after approval.
```

### Review-comment request

```text
Use $gh-address-comments to collect PR comments for the current branch.
List the comment items first, then apply only the ones I select.
```

## Strict Gate Policy

- `mypy` 실패 시 CI 실패
- `bandit` 실패 시 CI 실패
- 단위 테스트 실패 시 CI 실패
- 실패를 `|| true`로 무시하지 않음

## Release Checklist

```bash
python scripts/release_preflight.py
python scripts/validate_release_manifest.py
python scripts/validate_release_manifest.py --manifest .release/manifests/release-packaging-policy.txt --source staged
python scripts/validate_release_manifest.py --manifest .release/manifests/release-ci-platform.txt --source staged
python scripts/validate_release_manifest.py --manifest .release/manifests/release-scheduler-reliability.txt --source staged
python scripts/validate_release_manifest.py --manifest .release/manifests/release-runtime-binary-bootstrap.txt --source staged
python -m scripts.devtools.dev_entrypoint check --full
```

## Workflow Directory Contract

`.github/workflows/README.md`와 실제 파일 목록은 항상 1:1로 유지합니다.

## PR 운영 템플릿

- RR 이슈 템플릿: `.github/ISSUE_TEMPLATE/review-request.yml`
- 기본 PR 템플릿: `.github/pull_request_template.md`
- Repo hygiene/구조 정리 PR: `.github/PULL_REQUEST_TEMPLATE/repo_hygiene.md`
- 릴리즈 통합 PR: `.github/PULL_REQUEST_TEMPLATE/release_integration.md`
- Commit 템플릿: `.gitmessage.txt`
- skill 요청 예시: `docs/dev/AGENT_SKILL_REQUEST_PLAYBOOK.md`
- 로컬 템플릿 설정: `./scripts/devtools/setup_git_message_template.sh`
