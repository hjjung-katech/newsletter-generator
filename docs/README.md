# Documentation Hub

이 문서는 프로젝트 문서의 진입점이며, 주제별 정본(SSOT)을 고정합니다.

## Canonical Documents (SSOT)

| 영역 | 정본 문서 | 비고 |
|---|---|---|
| 설치 | [`setup/INSTALLATION.md`](setup/INSTALLATION.md) | 공통 설치/초기 설정 |
| 로컬 개발 | [`setup/LOCAL_SETUP.md`](setup/LOCAL_SETUP.md) | 개발/디버깅/로컬 실행 |
| 배포 | [`setup/RAILWAY_DEPLOYMENT.md`](setup/RAILWAY_DEPLOYMENT.md) | Railway 멀티서비스 운영 |
| CLI 사용법 | [`user/CLI_REFERENCE.md`](user/CLI_REFERENCE.md) | 옵션/명령/예시 |
| 환경변수 계약 | [`reference/environment-variables.md`](reference/environment-variables.md) | canonical env + 호환/폐기 정책 |
| Web API 계약 | [`reference/web-api.md`](reference/web-api.md) | Flask API 스키마/엔드포인트 |
| 리포 구조/운영 전략 | [`dev/LONG_TERM_REPO_STRATEGY.md`](dev/LONG_TERM_REPO_STRATEGY.md) | 장기 구조 개편/운영 플레이북 |
| Repo hygiene 정책 | [`dev/REPO_HYGIENE_POLICY.md`](dev/REPO_HYGIENE_POLICY.md) | 루트 분류/soft gate/dot 추적 범위 |
| 문서 전수조사표 | [`DOCUMENT_INVENTORY.md`](DOCUMENT_INVENTORY.md) | 문서 상태/owner/disposition 정리 |
| AGENTS/Skill 거버넌스 | [`dev/AGENTS_GOVERNANCE.md`](dev/AGENTS_GOVERNANCE.md) | 글로벌/레포/하위 AGENTS precedence와 skill 경계 |
| PR/Commit/Branch 프로세스 | [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md) | 템플릿 경로 + PR policy check gate |

## Audience Paths

- 사용자
  - [`setup/QUICK_START_GUIDE.md`](setup/QUICK_START_GUIDE.md)
  - [`user/USER_GUIDE.md`](user/USER_GUIDE.md)
  - [`user/CLI_REFERENCE.md`](user/CLI_REFERENCE.md)
  - [`user/MULTI_LLM_GUIDE.md`](user/MULTI_LLM_GUIDE.md)
  - [`user/email-sending.md`](user/email-sending.md)

- 개발자
  - [`dev/DEVELOPMENT_GUIDE.md`](dev/DEVELOPMENT_GUIDE.md)
  - [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md)
  - [`dev/LOCAL_CI_GUIDE.md`](dev/LOCAL_CI_GUIDE.md)
  - [`dev/LONG_TERM_REPO_STRATEGY.md`](dev/LONG_TERM_REPO_STRATEGY.md)
  - [`dev/REPO_HYGIENE_POLICY.md`](dev/REPO_HYGIENE_POLICY.md)
  - [`dev/AGENT_SKILL_REQUEST_PLAYBOOK.md`](dev/AGENT_SKILL_REQUEST_PLAYBOOK.md)
  - [`dev/AGENTS_GOVERNANCE.md`](dev/AGENTS_GOVERNANCE.md)
  - [`developer/CENTRALIZED_SETTINGS_GUIDE.md`](developer/CENTRALIZED_SETTINGS_GUIDE.md)
  - [`technical/LLM_CONFIGURATION.md`](technical/LLM_CONFIGURATION.md)

- 운영/배포
  - [`setup/RAILWAY_DEPLOYMENT.md`](setup/RAILWAY_DEPLOYMENT.md)
  - [`setup/WINDOWS_EXE_OPERATIONS.md`](setup/WINDOWS_EXE_OPERATIONS.md)
  - [`setup/WINDOWS_EXE_UPDATE_CHANNEL.md`](setup/WINDOWS_EXE_UPDATE_CHANNEL.md)
  - [`setup/WINDOWS_RELEASE_ADMIN_LOG_2026-02-24.md`](setup/WINDOWS_RELEASE_ADMIN_LOG_2026-02-24.md)
  - [`reference/web-api.md`](reference/web-api.md)
  - [`reference/environment-variables.md`](reference/environment-variables.md)

- 아키텍처/배경
  - [`ARCHITECTURE.md`](ARCHITECTURE.md)
  - [`technical/adr-0001-architecture-boundaries.md`](technical/adr-0001-architecture-boundaries.md)
  - [`technical/architecture-migration-log.md`](technical/architecture-migration-log.md)
  - [`technical/shim-deprecation-schedule.md`](technical/shim-deprecation-schedule.md)
  - [`PRD.md`](PRD.md)

## Governance

- 문서 상태/owner/disposition 기준: [`DOCUMENT_INVENTORY.md`](DOCUMENT_INVENTORY.md)
- archive 정책: [`archive/README.md`](archive/README.md)
- 2026-Q1 archive 인덱스: [`archive/2026-q1/README.md`](archive/2026-q1/README.md)

## Rules

1. 같은 사실은 한 문서에만 정본으로 유지합니다.
2. 다른 문서에는 복붙 대신 링크만 둡니다.
3. 인터페이스 변경(PR) 시 정본 문서를 먼저 갱신합니다.
4. 문서 링크는 CI/로컬 스캔에서 0건을 유지합니다.

## Historical / Archived Docs

아래 문서는 이력/분석 성격으로, 운영 정본으로 사용하지 않습니다.

- archive location:
  - [`archive/2026-q1/MAIN_INTEGRATION_EXECUTION_PLAN.md`](archive/2026-q1/MAIN_INTEGRATION_EXECUTION_PLAN.md)
  - [`archive/2026-q1/BRANCH_MAIN_GAP_ANALYSIS.md`](archive/2026-q1/BRANCH_MAIN_GAP_ANALYSIS.md)
  - [`archive/2026-q1/REFACTORING_EXECUTION_PLAN.md`](archive/2026-q1/REFACTORING_EXECUTION_PLAN.md)
  - [`archive/2026-q1/UNIFIED_ARCHITECTURE.md`](archive/2026-q1/UNIFIED_ARCHITECTURE.md)
  - [`archive/2026-q1/REPO_HYGIENE_STATUS_2026-02-24.md`](archive/2026-q1/REPO_HYGIENE_STATUS_2026-02-24.md)
  - [`archive/2026-q1/F14_COMPLETION_REPORT.md`](archive/2026-q1/F14_COMPLETION_REPORT.md)
  - [`archive/2026-q1/FIXES_SUMMARY.md`](archive/2026-q1/FIXES_SUMMARY.md)
  - [`archive/2026-q1/PROJECT_STRUCTURE.md`](archive/2026-q1/PROJECT_STRUCTURE.md)
  - [`archive/2026-q1/CODE_QUALITY.md`](archive/2026-q1/CODE_QUALITY.md)
  - [`archive/2026-q1/RR_REQUEST_TEMPLATE.md`](archive/2026-q1/RR_REQUEST_TEMPLATE.md)
  - [`archive/2026-q1/WORKFLOW_TEMPLATES.md`](archive/2026-q1/WORKFLOW_TEMPLATES.md)
  - [`archive/2026-q1/MULTI_LLM_IMPLEMENTATION_SUMMARY.md`](archive/2026-q1/MULTI_LLM_IMPLEMENTATION_SUMMARY.md)
  - [`archive/webservice-prd.md`](archive/webservice-prd.md)
