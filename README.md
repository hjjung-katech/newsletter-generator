# Newsletter Generator

[![CI/CD Pipeline](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/ci.yml)
[![Code Quality](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/code-quality.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/code-quality.yml)
[![Docs Quality](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Deploy Guide (Railway)](https://img.shields.io/badge/deploy-Railway-0B0D0E?logo=railway)](docs/setup/RAILWAY_DEPLOYMENT.md)

키워드/도메인 기반으로 최신 뉴스를 수집하고, AI로 요약된 HTML 뉴스레터를 생성·발송하는 프로젝트입니다.

## 핵심 포인트

- Canonical runtime: `Flask + Postmark`
- 문서 정본(SSOT) 기반 운영: `docs/README.md`
- 로컬/배포 모두 동일한 품질 게이트 사용: `run_ci_checks.py`, `make docs-check`

## 빠른 링크

- 문서 허브: `docs/README.md`
- 환경변수 계약: `docs/reference/environment-variables.md`
- Web API 계약: `docs/reference/web-api.md`
- Railway 배포: `docs/setup/RAILWAY_DEPLOYMENT.md`
- 개발 가이드: `docs/dev/DEVELOPMENT_GUIDE.md`

## Quickstart (5분)

1. 저장소 준비
```bash
git clone https://github.com/hjjung-katech/newsletter-generator.git
cd newsletter-generator
```

2. 가상환경/의존성 설치
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. 환경변수 설정
```bash
cp env.example .env
```

필수/선택 변수는 정본 문서를 참고하세요:
- `docs/reference/environment-variables.md`

4. 웹 실행
```bash
cd web
python init_database.py
python app.py
```

접속: `http://localhost:5000`

5. CLI 예시
```bash
cd ..
python -m newsletter.cli run --keywords "AI,반도체" --period 7 --template-style compact
```

## 문서 허브

- 전체 문서 안내: `docs/README.md`

정본(SSOT):
- 설치: `docs/setup/INSTALLATION.md`
- 로컬 개발: `docs/setup/LOCAL_SETUP.md`
- Railway 배포: `docs/setup/RAILWAY_DEPLOYMENT.md`
- CLI 참조: `docs/user/CLI_REFERENCE.md`
- 환경변수 계약: `docs/reference/environment-variables.md`
- Web API 계약: `docs/reference/web-api.md`

## 품질 게이트

```bash
python run_ci_checks.py --fix --full
```

## 기여

- 개발 가이드: `docs/dev/DEVELOPMENT_GUIDE.md`
- AGENTS 규칙: `AGENTS.md`

## 라이선스

- `LICENSE`
