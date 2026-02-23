# CI/CD Guide

## Overview

이 문서는 현재 운영 중인 CI/CD 파이프라인의 정본 가이드입니다.

## Active GitHub Actions Workflows

현재 운영 워크플로우는 아래 5개입니다.

1. `main-ci.yml`
- 코드 품질, 테스트, 빌드 검증
- 주요 브랜치 push/PR에서 실행
- PR 이벤트에서는 프로세스 계약(브랜치명 규칙 + PR 템플릿 섹션)도 검사

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

## Local Gate Commands

표준 로컬 게이트는 Makefile 엔트리로 고정합니다.

```bash
cd /Users/hojungjung/development/newsletter-generator
make bootstrap
make doctor
make check
make check-full
make repo-audit
```

- `make check`: 빠른 로컬 게이트
- `make check-full`: PR 전 전체 게이트
- `make repo-audit`: 루트 인벤토리 + repo hygiene soft gate 리포트 생성
- dev 유틸 실행 스크립트는 `scripts/devtools/`를 기본 경로로 사용합니다.

## Repo Hygiene Soft Gate

`main-ci.yml`의 `quality-checks` 단계에서 아래 soft gate를 실행합니다.

```bash
python scripts/repo_audit.py \
  --policy scripts/repo_hygiene_policy.json \
  --output-dir artifacts/repo-audit \
  --check-policy
```

- Week 1~2 운영: warning-only
- CI artifact:
  - `artifacts/repo-audit/repo_audit_report.md`
  - `artifacts/repo-audit/repo_audit_report.json`
  - `artifacts/repo-audit/policy_warnings.md`

## PR Process Contract Gate

`main-ci.yml`의 `quality-checks` 단계에서 PR일 때 아래를 검사합니다.

1. 브랜치명 정책
- 형식: `<type>/<kebab-case-topic>`
- 허용 타입: `codex|feature|fix|bugfix|hotfix|chore|docs|refactor|test|release`

2. PR 본문 템플릿 섹션
- 기본 템플릿: `.github/pull_request_template.md`
- 특화 템플릿: `.github/PULL_REQUEST_TEMPLATE/release_integration.md`

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

- RR 요청 템플릿: `docs/dev/RR_REQUEST_TEMPLATE.md`
- 기본 PR 템플릿: `.github/pull_request_template.md`
- Repo hygiene/구조 정리 PR: `.github/PULL_REQUEST_TEMPLATE/repo_hygiene.md`
- 릴리즈 통합 PR: `.github/PULL_REQUEST_TEMPLATE/release_integration.md`
- Commit 템플릿: `.github/COMMIT_TEMPLATE.txt`
- 로컬 템플릿 설정: `./scripts/devtools/setup_git_message_template.sh`
