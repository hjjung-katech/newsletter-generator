# CI/CD Guide

## Overview

이 문서는 현재 운영 중인 CI/CD 파이프라인의 정본 가이드입니다.

## Active GitHub Actions Workflows

현재 운영 워크플로우는 아래 4개입니다.

1. `main-ci.yml`
- 코드 품질, 테스트, 빌드 검증
- 주요 브랜치 push/PR에서 실행

2. `deployment.yml`
- 배포 파이프라인 (Railway + Pages 병행)
- `main` push, 스케줄, 수동 실행

3. `security-scan.yml`
- 정기 보안 스캔
- 스케줄/수동 실행

4. `docs-quality.yml`
- Markdown 링크/스타일 품질 검증
- 문서 변경 push/PR에서 실행

## Local Gate Commands

표준 로컬 게이트는 Makefile 엔트리로 고정합니다.

```bash
cd /Users/hojungjung/development/newsletter-generator
make bootstrap
make doctor
make check
make check-full
```

- `make check`: 빠른 로컬 게이트
- `make check-full`: PR 전 전체 게이트

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
