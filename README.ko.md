# Newsletter Generator
[English](README.md) | [한국어](README.ko.md)

[![Main CI](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/main-ci.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/main-ci.yml)
[![Docs Quality](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml)
[![Security Scan](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/security-scan.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/security-scan.yml)
[![Python 3.11 | 3.12](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Deploy Guide (Railway)](https://img.shields.io/badge/deploy-Railway-0B0D0E?logo=railway)](docs/setup/RAILWAY_DEPLOYMENT.md)

원시 프로젝트 업데이트를 구조화된 뉴스레터로 자동 변환해 메인테이너의 커뮤니케이션 부담을 줄이는 도구입니다.

오픈소스 메인테이너, 소규모 팀, 사내 기술 커뮤니케이션 워크플로를 위해 설계되었습니다.

- 원시 메모를 공유 가능한 뉴스레터 초안으로 변환
- 릴리스 노트와 반복 업데이트 정리에 드는 시간 절감
- 웹 기반 흐름으로 비엔지니어도 사용 가능
- 크로스플랫폼 환경과 이메일 배포 워크플로 지원

## Quick Demo
기본 `compact` 출력 구조를 보여주는 정적 preview입니다.

**입력**

```text
Title: Maintainer Communication Brief
Topic: Maintainer workflow automation
Date: 2026-03-19
Issue: 14
Tagline: Turn weekly project activity into a concise update teams can actually use.
Audience: Prepared for contributors, internal stakeholders, and partner teams.

[Top Stories]
- Release notes drafts now start from merged pull requests | The weekly changelog is pre-assembled from merged PR metadata, leaving maintainers with a short editorial pass instead of a full rewrite. | Project activity · 2026-03-19

[Project Delivery]
Intro: Updates that reduce repetitive maintainer coordination work.
- Weekly digest draft is prepared from project activity and issue labels | Release workflow · 2026-03-19

[Definitions]
- Idempotency key | A stable request identifier used to prevent duplicate jobs or duplicate email sends.

[Things to Watch]
- If GitHub issue and pull request summaries are added next, maintainers can publish weekly updates with much less manual editing.
```

**출력**

```md
# Maintainer Communication Brief
_Maintainer workflow automation · Issue 14 · 2026-03-19_

_Turn weekly project activity into a concise update teams can actually use._

Prepared for contributors, internal stakeholders, and partner teams.

## 🔥 Must-Read This Week
### Release notes drafts now start from merged pull requests
The weekly changelog is pre-assembled from merged PR metadata, leaving maintainers with a short editorial pass instead of a full rewrite.
_Project activity · 2026-03-19_

## Project Delivery
Updates that reduce repetitive maintainer coordination work.

- **Weekly digest draft is prepared from project activity and issue labels** (`Release workflow · 2026-03-19`)

## 📖 Definitions
- **Idempotency key:** A stable request identifier used to prevent duplicate jobs or duplicate email sends.

## 💡 Things to Watch
> If GitHub issue and pull request summaries are added next, maintainers can publish weekly updates with much less manual editing.
```

## 개요
메인테이너와 팀은 업데이트를 요약하고 대상별로 다시 쓰는 데 많은 시간을 씁니다. Newsletter Generator는 이 반복 업무를 줄이기 위해 만들어졌습니다. 프로젝트 업데이트 메모를 받아 커뮤니티 공지, 내부 공유, 팀 브리프에 바로 쓸 수 있는 뉴스레터 형태로 정리합니다.

실제 앱은 `compact`, `detailed`, `email_compatible` HTML 템플릿을 지원합니다. 이 README는 기본값인 `compact` 구조를 영어 기준의 정적 preview로 보여주고, 현재 저장소에 포함된 운영용 템플릿 문구는 한국어 중심입니다. 이 저장소는 단순 소개만 담지 않고 실제 운영에 필요한 정보도 함께 유지합니다. 지원 정책, 환경변수 계약, 로컬 실행 가이드, 배포 문서, 검증 게이트를 README와 `docs/`에서 함께 안내해 신규 사용자와 유지보수자가 빠르게 진입할 수 있도록 구성했습니다.

## 사용 사례
- 오픈소스 메인테이너가 주간 또는 월간 프로젝트 업데이트를 기여자와 사용자에게 공유할 때
- 작은 팀이 엔지니어에게 매번 직접 요약을 부탁하지 않고 부서 간 진행 상황을 알릴 때
- 사내 제품, 플랫폼, 운영 조직이 도메인별 기술 업데이트를 팀 간에 공유할 때
- 커뮤니티 다이제스트, 이해관계자 브리프, 팀 뉴스레터 같은 반복 커뮤니케이션 워크플로를 자동화할 때

## 주요 기능
- 원시 업데이트를 자동으로 요약해 구조화된 공유용 뉴스레터로 변환
- 커뮤니티 공지와 내부 배포에 바로 쓸 수 있는 정돈된 뉴스레터 초안 생성
- 릴리스 노트, 상태 보고, 반복 업데이트 정리에 드는 시간 절감
- 반복 커뮤니케이션 워크플로를 위한 이메일 배포 지원
- 웹 기반의 크로스플랫폼 흐름으로 비엔지니어도 쉽게 사용할 수 있는 사용성

## 예시 출력
생성 결과 예시는 다음과 같습니다. 아래 예시는 영문 공개 데모 기준이지만, 실제 구조는 기본 `compact` 템플릿 흐름을 따릅니다.

```md
# Maintainer Communication Brief
_Maintainer workflow automation · Issue 14 · 2026-03-19_

_Turn weekly project activity into a concise update teams can actually use._

Prepared for contributors, internal stakeholders, and partner teams.

## 🔥 Must-Read This Week
### Release notes drafts now start from merged pull requests
The weekly changelog is pre-assembled from merged PR metadata, leaving maintainers with a short editorial pass instead of a full rewrite.
_Project activity · 2026-03-19_

### Docs quality checks now catch broken anchors before publish
Maintainers can fix link and reference regressions before updates go out to contributors or internal readers.
_Docs pipeline · 2026-03-18_

## Project Delivery
Updates that reduce repetitive maintainer coordination work.

- **Weekly digest draft is prepared from project activity and issue labels** (`Release workflow · 2026-03-19`)
- **Issue intake wording was simplified so non-engineers can report docs and deployment gaps faster** (`Support workflow · 2026-03-18`)

## Contributor Experience
Improvements that make updates easier to consume across community and internal audiences.

- **A single onboarding summary now answers the most repeated contributor setup questions** (`Contributor docs · 2026-03-17`)
- **Cross-team platform notes are grouped into one digest instead of separate status emails** (`Internal communications · 2026-03-17`)

## 📖 Definitions
- **Idempotency key:** A stable request identifier used to prevent duplicate jobs or duplicate email sends.
- **Docs gate:** An automated check that verifies documentation links, required references, and policy consistency.

## 💡 Things to Watch
> If GitHub issue and pull request summaries are added next, maintainers can publish weekly updates with much less manual editing.

_Generated as an English compact preview of the production newsletter template._
```

## 왜 중요한가
메인테이너는 이미 리뷰, 이슈 분류, 릴리스 준비에 많은 시간을 쓰고 있습니다. 커뮤니케이션은 꼭 필요하지만 또 하나의 수작업 백로그가 되어서는 안 됩니다. 이 프로젝트는 업데이트 정리, 릴리스 노트, 이해관계자 보고처럼 커뮤니케이션 비중이 큰 워크플로에서 maintainer workload를 직접 줄이는 데 초점을 맞춥니다.

## 시작 가이드
1. 빠른 시작: [`docs/setup/QUICK_START_GUIDE.md`](docs/setup/QUICK_START_GUIDE.md)
2. 지원 정책: [`docs/reference/support-policy.md`](docs/reference/support-policy.md)
3. 환경변수 계약: [`docs/reference/environment-variables.md`](docs/reference/environment-variables.md)
4. 로컬 개발: [`docs/setup/LOCAL_SETUP.md`](docs/setup/LOCAL_SETUP.md)
5. 검증 게이트: `python -m scripts.devtools.dev_entrypoint check`, `python -m scripts.devtools.dev_entrypoint check --full`

공식 지원 범위와 운영 기준은 지원 정책 문서를 따릅니다. 요약하면 Python 3.11, 3.12가 주요 대상이고 Linux는 canonical production server, Windows는 native desktop bundle 대상, macOS는 source-based development와 smoke 중심 지원입니다.

## 빠른 시작
위 Quick Demo는 정적 preview입니다. 실제 제품을 로컬에서 실행하려면 아래 canonical setup과 CLI entrypoint를 사용하면 됩니다.

```bash
git clone https://github.com/hjjung-katech/newsletter-generator.git
cd newsletter-generator
python -m scripts.devtools.dev_entrypoint bootstrap
cp .env.example .env
python -m scripts.devtools.dev_entrypoint check
python -m scripts.devtools.dev_entrypoint run newsletter run --keywords "open source, maintainer tooling"
```

## CLI 사용법
소스 체크아웃 기준 canonical entrypoint:

```bash
python -m scripts.devtools.dev_entrypoint run web
python web/init_database.py
python -m scripts.devtools.dev_entrypoint run newsletter run --keywords "open source, maintainer tooling"
python -m scripts.devtools.dev_entrypoint run newsletter run --keywords "open source, maintainer tooling" --template-style compact
```

패키지를 설치한 환경에서는 다음 CLI도 사용할 수 있습니다.

```bash
newsletter run --keywords "open source, maintainer tooling"
```

## 로드맵
- GitHub 연동으로 저장소 업데이트를 직접 가져오기
- PR과 이슈 요약을 기반으로 한 maintainer 다이제스트 자동화
- 릴리스 노트와 이해관계자 업데이트 자동 생성

## 주요 문서
| 목적 | 문서 |
|---|---|
| 문서 허브 | [`docs/README.md`](docs/README.md) |
| 문서 인벤토리 | [`docs/DOCUMENT_INVENTORY.md`](docs/DOCUMENT_INVENTORY.md) |
| 설치와 온보딩 | [`docs/setup/INSTALLATION.md`](docs/setup/INSTALLATION.md), [`docs/setup/QUICK_START_GUIDE.md`](docs/setup/QUICK_START_GUIDE.md) |
| 로컬 개발 | [`docs/setup/LOCAL_SETUP.md`](docs/setup/LOCAL_SETUP.md), [`docs/dev/DEVELOPMENT_GUIDE.md`](docs/dev/DEVELOPMENT_GUIDE.md) |
| 지원 정책, API, 환경변수 계약 | [`docs/reference/support-policy.md`](docs/reference/support-policy.md), [`docs/reference/web-api.md`](docs/reference/web-api.md), [`docs/reference/environment-variables.md`](docs/reference/environment-variables.md) |
| 배포 | [`docs/setup/RAILWAY_DEPLOYMENT.md`](docs/setup/RAILWAY_DEPLOYMENT.md) |
| 저장소 전략과 위생 | [`docs/dev/LONG_TERM_REPO_STRATEGY.md`](docs/dev/LONG_TERM_REPO_STRATEGY.md), [`docs/dev/REPO_HYGIENE_POLICY.md`](docs/dev/REPO_HYGIENE_POLICY.md) |

## 기여
- RR 템플릿: [`.github/ISSUE_TEMPLATE/review-request.yml`](.github/ISSUE_TEMPLATE/review-request.yml)
- PR 템플릿: [`.github/pull_request_template.md`](.github/pull_request_template.md)
- 커밋 템플릿: [`.gitmessage.txt`](.gitmessage.txt)
- 저장소 규칙: [`AGENTS.md`](AGENTS.md)

## 라이선스
`LICENSE`
