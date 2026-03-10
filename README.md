# Newsletter Generator

[![Main CI](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/main-ci.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/main-ci.yml)
[![Docs Quality](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml)
[![Security Scan](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/security-scan.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/security-scan.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Deploy Guide (Railway)](https://img.shields.io/badge/deploy-Railway-0B0D0E?logo=railway)](docs/setup/RAILWAY_DEPLOYMENT.md)

키워드/도메인 기반으로 최신 뉴스를 수집하고 AI 요약 HTML 뉴스레터를 생성·발송하는 프로젝트입니다.

## Start Here (5분)

1. 빠른 시작: [`docs/setup/QUICK_START_GUIDE.md`](docs/setup/QUICK_START_GUIDE.md)
2. 환경변수 계약(SSOT): [`docs/reference/environment-variables.md`](docs/reference/environment-variables.md)
3. 로컬 개발 가이드: [`docs/setup/LOCAL_SETUP.md`](docs/setup/LOCAL_SETUP.md)
4. 품질 게이트: `make check`, `make check-full`

루트는 개요와 진입 링크만 유지하고, 상세 설명은 `docs/` 정본 문서로 관리합니다.

## Minimal Commands

```bash
git clone https://github.com/hjjung-katech/newsletter-generator.git
cd newsletter-generator
make bootstrap
cp .env.example .env
make check
```

Experimental FastAPI entrypoint uses a separate sample at
[`apps/experimental/.env.example`](apps/experimental/.env.example).

소스 체크아웃 기준 canonical entrypoints:

```bash
python web/init_database.py
python -m web.app
python -m newsletter run --keywords "AI"
```

웹 실행/CLI/배포 절차는 아래 정본 문서를 사용하세요.

## Docs Hub

| 목적 | 문서 |
|---|---|
| 문서 허브(SSOT) | [`docs/README.md`](docs/README.md) |
| 문서 전수조사표 | [`docs/DOCUMENT_INVENTORY.md`](docs/DOCUMENT_INVENTORY.md) |
| 설치/온보딩 | [`docs/setup/INSTALLATION.md`](docs/setup/INSTALLATION.md), [`docs/setup/QUICK_START_GUIDE.md`](docs/setup/QUICK_START_GUIDE.md) |
| 로컬 개발 | [`docs/setup/LOCAL_SETUP.md`](docs/setup/LOCAL_SETUP.md), [`docs/dev/DEVELOPMENT_GUIDE.md`](docs/dev/DEVELOPMENT_GUIDE.md) |
| API/환경변수 계약 | [`docs/reference/web-api.md`](docs/reference/web-api.md), [`docs/reference/environment-variables.md`](docs/reference/environment-variables.md) |
| 배포 | [`docs/setup/RAILWAY_DEPLOYMENT.md`](docs/setup/RAILWAY_DEPLOYMENT.md) |
| 구조/운영 전략 | [`docs/dev/LONG_TERM_REPO_STRATEGY.md`](docs/dev/LONG_TERM_REPO_STRATEGY.md), [`docs/dev/REPO_HYGIENE_POLICY.md`](docs/dev/REPO_HYGIENE_POLICY.md) |

## 기여

- RR 템플릿: [`.github/ISSUE_TEMPLATE/review-request.yml`](.github/ISSUE_TEMPLATE/review-request.yml)
- PR 템플릿: [`.github/pull_request_template.md`](.github/pull_request_template.md)
- 커밋 템플릿: [`.gitmessage.txt`](.gitmessage.txt)
- 운영 규칙: [`AGENTS.md`](AGENTS.md)

## 라이선스

- `LICENSE`
