# CI/CD Guide

## Overview

이 문서는 현재 운영 중인 CI/CD 파이프라인의 정본 가이드입니다.

## Active GitHub Actions Workflows

현재 운영 워크플로우는 아래 6개입니다.

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

## Local Gate Commands

표준 로컬 게이트는 Makefile 엔트리로 고정합니다.

```bash
cd /Users/hojungjung/development/newsletter-generator
make bootstrap
make doctor
make check
make check-full
make repo-audit
make repo-audit-strict
```

- `make check`: 빠른 로컬 게이트
- `make check-full`: PR 전 전체 게이트
- `make repo-audit`: 루트 인벤토리 + repo hygiene soft gate 리포트 생성
- `make repo-audit-strict`: CI hard gate와 동일(strict) 경로 점검
- dev 유틸 실행 스크립트는 `scripts/devtools/`를 기본 경로로 사용합니다.

## Repo Hygiene Gate

`main-ci.yml`의 `quality-checks` 단계에서 repo hygiene gate를 실행합니다.

```bash
python scripts/repo_audit.py \
  --policy scripts/repo_hygiene_policy.json \
  --output-dir artifacts/repo-audit \
  --check-policy
```

- 현재 기본 운영: `REPO_HYGIENE_STRICT=true` (hard gate)
- 임시 예외 경로: `REPO_HYGIENE_STRICT=false`로 soft gate override 가능(권장하지 않음)
- CI artifact:
  - `artifacts/repo-audit/repo_audit_report.md`
  - `artifacts/repo-audit/repo_audit_report.json`
  - `artifacts/repo-audit/policy_warnings.md`

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

## Strict Gate Policy

- `mypy` 실패 시 CI 실패
- `bandit` 실패 시 CI 실패
- 단위 테스트 실패 시 CI 실패
- 실패를 `|| true`로 무시하지 않음

## Release Checklist

```bash
python scripts/release_preflight.py
python scripts/validate_release_manifest.py --manifest .release/manifests/release-ci-platform.txt --source staged
python scripts/validate_release_manifest.py --manifest .release/manifests/release-scheduler-reliability.txt --source staged
python scripts/validate_release_manifest.py --manifest .release/manifests/release-runtime-binary-bootstrap.txt --source staged
make check-full
```

## Workflow Directory Contract

`.github/workflows/README.md`와 실제 파일 목록은 항상 1:1로 유지합니다.

## PR 운영 템플릿

- RR 이슈 템플릿: `.github/ISSUE_TEMPLATE/review-request.yml`
- 기본 PR 템플릿: `.github/pull_request_template.md`
- Repo hygiene/구조 정리 PR: `.github/PULL_REQUEST_TEMPLATE/repo_hygiene.md`
- 릴리즈 통합 PR: `.github/PULL_REQUEST_TEMPLATE/release_integration.md`
- Commit 템플릿: `.gitmessage.txt`
- 워크플로 템플릿 가이드: `docs/dev/WORKFLOW_TEMPLATES.md`
- 로컬 템플릿 설정: `./scripts/devtools/setup_git_message_template.sh`
