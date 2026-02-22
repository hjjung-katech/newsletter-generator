# Documentation Hub

이 문서는 프로젝트 문서의 진입점이며, 주제별 정본(SSOT)을 고정합니다.

## Canonical Documents (SSOT)

| 영역 | 정본 문서 | 비고 |
|---|---|---|
| 설치 | `setup/INSTALLATION.md` | 공통 설치/초기 설정 |
| 로컬 개발 | `setup/LOCAL_SETUP.md` | 개발/디버깅/로컬 실행 |
| 배포 | `setup/RAILWAY_DEPLOYMENT.md` | Railway 멀티서비스 운영 |
| CLI 사용법 | `user/CLI_REFERENCE.md` | 옵션/명령/예시 |
| 환경변수 계약 | `reference/environment-variables.md` | canonical env + 호환/폐기 정책 |
| Web API 계약 | `reference/web-api.md` | Flask API 스키마/엔드포인트 |

## Audience Paths

- 사용자
  - `setup/QUICK_START_GUIDE.md`
  - `user/USER_GUIDE.md`
  - `user/CLI_REFERENCE.md`
  - `user/MULTI_LLM_GUIDE.md`
  - `user/email-sending.md`

- 개발자
  - `dev/DEVELOPMENT_GUIDE.md`
  - `dev/CI_CD_GUIDE.md`
  - `dev/REFACTORING_EXECUTION_PLAN.md`
  - `developer/CENTRALIZED_SETTINGS_GUIDE.md`
  - `technical/LLM_CONFIGURATION.md`

- 운영/배포
  - `setup/RAILWAY_DEPLOYMENT.md`
  - `reference/web-api.md`
  - `reference/environment-variables.md`

- 아키텍처/배경
  - `ARCHITECTURE.md`
  - `UNIFIED_ARCHITECTURE.md`
  - `PRD.md`

## Rules

1. 같은 사실은 한 문서에만 정본으로 유지합니다.
2. 다른 문서에는 복붙 대신 링크만 둡니다.
3. 인터페이스 변경(PR) 시 정본 문서를 먼저 갱신합니다.
4. 문서 링크는 CI/로컬 스캔에서 0건을 유지합니다.

## Historical / Internal Docs

아래 문서는 이력/분석 성격으로, 운영 정본으로 사용하지 않습니다.

- `dev/BRANCH_MAIN_GAP_ANALYSIS.md`
- `dev/MAIN_INTEGRATION_EXECUTION_PLAN.md`
- `FIXES_SUMMARY.md`
- `PROJECT_STRUCTURE.md`
- `archive/webservice-prd.md`
