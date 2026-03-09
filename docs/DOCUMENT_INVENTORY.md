# Document Inventory

문서 정합성 전수조사 기준일: 2026-03-09

이 문서는 현재 추적 중인 Markdown 문서 55개를 대상으로 `canonical`, `supporting`, `historical`, `obsolete` 상태를 지정한 인벤토리입니다.
owner는 개인 이름이 아니라 기능 영역 기준 관리 책임입니다.

## Status Definitions

- `canonical`: 해당 사실의 정본. 변경 시 가장 먼저 갱신해야 하는 문서
- `supporting`: 사용/운영/개발을 돕는 보조 문서. 정본을 링크하고 중복 설명은 최소화
- `historical`: 배경, 로그, 완료 보고서, 기준선 스냅샷. 운영 정본으로 사용하지 않음
- `obsolete`: 현재 상태와 어긋나거나 정본과 중복된 문서. archive 또는 삭제 대상

## Repo Entry Docs

| Path | Status | Owner | Canonical Replacement | Disposition |
|---|---|---|---|---|
| [`../README.md`](../README.md) | canonical | Docs/Onboarding | - | keep |
| [`../CHANGELOG.md`](../CHANGELOG.md) | supporting | Release/Ops | - | keep |
| [`../AGENTS.md`](../AGENTS.md) | canonical | Repo Governance | - | keep |
| [`../web/AGENTS.md`](../web/AGENTS.md) | canonical | Web Runtime | - | keep |

## Docs Root

| Path | Status | Owner | Canonical Replacement | Disposition |
|---|---|---|---|---|
| [`README.md`](README.md) | canonical | Docs/Onboarding | - | keep |
| [`DOCUMENT_INVENTORY.md`](DOCUMENT_INVENTORY.md) | canonical | Docs/Onboarding | - | keep |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | canonical | Architecture | - | keep |
| [`PRD.md`](PRD.md) | supporting | Product | - | keep |
| [`archive/2026-q1/UNIFIED_ARCHITECTURE.md`](archive/2026-q1/UNIFIED_ARCHITECTURE.md) | historical | Architecture | [`ARCHITECTURE.md`](ARCHITECTURE.md), [`technical/adr-0001-architecture-boundaries.md`](technical/adr-0001-architecture-boundaries.md) | archive |
| [`archive/README.md`](archive/README.md) | canonical | Repo Hygiene | - | keep |
| [`archive/webservice-prd.md`](archive/webservice-prd.md) | historical | Product | [`PRD.md`](PRD.md) | keep in archive |
| [`archive/2026-q1/FIXES_SUMMARY.md`](archive/2026-q1/FIXES_SUMMARY.md) | obsolete | Release/Ops | [`../CHANGELOG.md`](../CHANGELOG.md), [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md) | archive |
| [`archive/2026-q1/PROJECT_STRUCTURE.md`](archive/2026-q1/PROJECT_STRUCTURE.md) | obsolete | Repo Hygiene | [`dev/LONG_TERM_REPO_STRATEGY.md`](dev/LONG_TERM_REPO_STRATEGY.md), [`dev/REPO_HYGIENE_POLICY.md`](dev/REPO_HYGIENE_POLICY.md) | archive |

## Dev Docs

| Path | Status | Owner | Canonical Replacement | Disposition |
|---|---|---|---|---|
| [`dev/LONG_TERM_REPO_STRATEGY.md`](dev/LONG_TERM_REPO_STRATEGY.md) | canonical | Repo Hygiene | - | keep |
| [`dev/REPO_HYGIENE_POLICY.md`](dev/REPO_HYGIENE_POLICY.md) | canonical | Repo Hygiene | - | keep |
| [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md) | canonical | Contributor Workflow | - | keep |
| [`dev/DEVELOPMENT_GUIDE.md`](dev/DEVELOPMENT_GUIDE.md) | supporting | Contributor Workflow | [`../setup/LOCAL_SETUP.md`](setup/LOCAL_SETUP.md) | keep |
| [`dev/LOCAL_CI_GUIDE.md`](dev/LOCAL_CI_GUIDE.md) | supporting | Contributor Workflow | [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md) | keep |
| [`dev/CODE_QUALITY.md`](dev/CODE_QUALITY.md) | supporting | Contributor Workflow | [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md) | keep |
| [`dev/WORKFLOW_TEMPLATES.md`](dev/WORKFLOW_TEMPLATES.md) | supporting | Contributor Workflow | [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md) | keep |
| [`dev/RR_REQUEST_TEMPLATE.md`](dev/RR_REQUEST_TEMPLATE.md) | supporting | Contributor Workflow | [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md) | keep |
| [`dev/AGENT_SKILL_REQUEST_PLAYBOOK.md`](dev/AGENT_SKILL_REQUEST_PLAYBOOK.md) | supporting | Contributor Workflow | [`../AGENTS.md`](../AGENTS.md) | keep |
| [`dev/CODEX_INSTRUCTION_LAYOUT.md`](dev/CODEX_INSTRUCTION_LAYOUT.md) | supporting | Repo Governance | [`../AGENTS.md`](../AGENTS.md) | keep |
| [`dev/langsmith_setup.md`](dev/langsmith_setup.md) | supporting | Runtime Config | [`technical/LLM_CONFIGURATION.md`](technical/LLM_CONFIGURATION.md) | keep |
| [`archive/2026-q1/MAIN_INTEGRATION_EXECUTION_PLAN.md`](archive/2026-q1/MAIN_INTEGRATION_EXECUTION_PLAN.md) | historical | Release/Ops | [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md), [`dev/WORKFLOW_TEMPLATES.md`](dev/WORKFLOW_TEMPLATES.md) | archive |
| [`archive/2026-q1/BRANCH_MAIN_GAP_ANALYSIS.md`](archive/2026-q1/BRANCH_MAIN_GAP_ANALYSIS.md) | historical | Release/Ops | [`dev/CI_CD_GUIDE.md`](dev/CI_CD_GUIDE.md) | archive |
| [`archive/2026-q1/REFACTORING_EXECUTION_PLAN.md`](archive/2026-q1/REFACTORING_EXECUTION_PLAN.md) | historical | Repo Hygiene | [`dev/LONG_TERM_REPO_STRATEGY.md`](dev/LONG_TERM_REPO_STRATEGY.md), [`dev/REPO_HYGIENE_POLICY.md`](dev/REPO_HYGIENE_POLICY.md) | archive |
| [`archive/2026-q1/MULTI_LLM_IMPLEMENTATION_SUMMARY.md`](archive/2026-q1/MULTI_LLM_IMPLEMENTATION_SUMMARY.md) | historical | Architecture | [`technical/LLM_CONFIGURATION.md`](technical/LLM_CONFIGURATION.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) | archive |
| [`archive/2026-q1/REPO_HYGIENE_STATUS_2026-02-24.md`](archive/2026-q1/REPO_HYGIENE_STATUS_2026-02-24.md) | historical | Repo Hygiene | [`dev/REPO_HYGIENE_POLICY.md`](dev/REPO_HYGIENE_POLICY.md) | archive |
| [`archive/2026-q1/F14_COMPLETION_REPORT.md`](archive/2026-q1/F14_COMPLETION_REPORT.md) | historical | Runtime Config | [`developer/CENTRALIZED_SETTINGS_GUIDE.md`](developer/CENTRALIZED_SETTINGS_GUIDE.md) | archive |

## Reference, Setup, and User Docs

| Path | Status | Owner | Canonical Replacement | Disposition |
|---|---|---|---|---|
| [`reference/environment-variables.md`](reference/environment-variables.md) | canonical | Runtime Config | - | keep |
| [`reference/web-api.md`](reference/web-api.md) | canonical | Web Runtime | - | keep |
| [`setup/INSTALLATION.md`](setup/INSTALLATION.md) | canonical | Setup/Deploy | - | keep |
| [`setup/LOCAL_SETUP.md`](setup/LOCAL_SETUP.md) | canonical | Setup/Deploy | - | keep |
| [`setup/QUICK_START_GUIDE.md`](setup/QUICK_START_GUIDE.md) | supporting | Docs/Onboarding | [`setup/INSTALLATION.md`](setup/INSTALLATION.md) | keep |
| [`setup/RAILWAY_DEPLOYMENT.md`](setup/RAILWAY_DEPLOYMENT.md) | canonical | Setup/Deploy | - | keep |
| [`setup/PYINSTALLER_WINDOWS.md`](setup/PYINSTALLER_WINDOWS.md) | supporting | Setup/Deploy | [`setup/WINDOWS_EXE_OPERATIONS.md`](setup/WINDOWS_EXE_OPERATIONS.md) | keep |
| [`setup/WINDOWS_EXE_OPERATIONS.md`](setup/WINDOWS_EXE_OPERATIONS.md) | canonical | Setup/Deploy | - | keep |
| [`setup/WINDOWS_EXE_SMOKE_PLAYBOOK.md`](setup/WINDOWS_EXE_SMOKE_PLAYBOOK.md) | supporting | Setup/Deploy | [`setup/WINDOWS_EXE_OPERATIONS.md`](setup/WINDOWS_EXE_OPERATIONS.md) | keep |
| [`setup/WINDOWS_EXE_UPDATE_CHANNEL.md`](setup/WINDOWS_EXE_UPDATE_CHANNEL.md) | supporting | Setup/Deploy | [`setup/WINDOWS_EXE_OPERATIONS.md`](setup/WINDOWS_EXE_OPERATIONS.md) | keep |
| [`setup/WINDOWS_RELEASE_ADMIN_LOG_2026-02-24.md`](setup/WINDOWS_RELEASE_ADMIN_LOG_2026-02-24.md) | historical | Setup/Deploy | [`setup/WINDOWS_EXE_OPERATIONS.md`](setup/WINDOWS_EXE_OPERATIONS.md) | keep |
| [`user/USER_GUIDE.md`](user/USER_GUIDE.md) | canonical | User Docs | - | keep |
| [`user/CLI_REFERENCE.md`](user/CLI_REFERENCE.md) | canonical | User Docs | - | keep |
| [`user/MULTI_LLM_GUIDE.md`](user/MULTI_LLM_GUIDE.md) | supporting | User Docs | [`technical/LLM_CONFIGURATION.md`](technical/LLM_CONFIGURATION.md) | keep |
| [`user/email-sending.md`](user/email-sending.md) | supporting | User Docs | [`reference/environment-variables.md`](reference/environment-variables.md), [`reference/web-api.md`](reference/web-api.md) | keep |

## Technical and Developer Internals

| Path | Status | Owner | Canonical Replacement | Disposition |
|---|---|---|---|---|
| [`developer/CENTRALIZED_SETTINGS_GUIDE.md`](developer/CENTRALIZED_SETTINGS_GUIDE.md) | supporting | Runtime Config | [`reference/environment-variables.md`](reference/environment-variables.md) | keep |
| [`technical/LLM_CONFIGURATION.md`](technical/LLM_CONFIGURATION.md) | canonical | Runtime Config | - | keep |
| [`technical/adr-0001-architecture-boundaries.md`](technical/adr-0001-architecture-boundaries.md) | canonical | Architecture | - | keep |
| [`technical/architecture-baseline-2026-02-22.md`](technical/architecture-baseline-2026-02-22.md) | historical | Architecture | [`technical/adr-0001-architecture-boundaries.md`](technical/adr-0001-architecture-boundaries.md) | keep |
| [`technical/architecture-migration-log.md`](technical/architecture-migration-log.md) | historical | Architecture | [`technical/adr-0001-architecture-boundaries.md`](technical/adr-0001-architecture-boundaries.md) | keep |
| [`technical/shim-deprecation-schedule.md`](technical/shim-deprecation-schedule.md) | supporting | Architecture | [`technical/adr-0001-architecture-boundaries.md`](technical/adr-0001-architecture-boundaries.md) | keep |

## Test Docs

| Path | Status | Owner | Canonical Replacement | Disposition |
|---|---|---|---|---|
| [`../tests/README.md`](../tests/README.md) | supporting | QA | [`dev/LOCAL_CI_GUIDE.md`](dev/LOCAL_CI_GUIDE.md) | keep |
| [`../tests/TEST_EXECUTION_GUIDE.md`](../tests/TEST_EXECUTION_GUIDE.md) | supporting | QA | [`../tests/README.md`](../tests/README.md) | keep |
| [`../tests/TEST_REPORT_COMPACT_DEFINITIONS.md`](../tests/TEST_REPORT_COMPACT_DEFINITIONS.md) | supporting | QA | [`../tests/README.md`](../tests/README.md) | keep |
| [`../tests/TEST_CLASSIFICATION_SUMMARY.md`](../tests/TEST_CLASSIFICATION_SUMMARY.md) | supporting | QA | [`../tests/README.md`](../tests/README.md) | keep |
| [`../tests/RESULTS_SUMMARY.md`](../tests/RESULTS_SUMMARY.md) | historical | QA | [`../tests/README.md`](../tests/README.md) | keep |

## Immediate Actions Applied in This RR

1. `obsolete` 또는 날짜가 박힌 완료 보고서 중 현재 운영 정본이 아닌 문서는 [`archive/2026-q1/`](archive/2026-q1/README.md) 로 이관했습니다.
2. archive-first 정책과 버킷 명명 규칙은 [`archive/README.md`](archive/README.md) 에서 관리합니다.
3. 허브 문서와 루트 README에는 인벤토리 링크를 추가해 문서 탐색 시작점을 단일화했습니다.
4. 환경변수 정본과 `.env.example` 의 용어를 맞추기 위해 canonical key와 compatibility key를 분리해 명시했습니다.
5. 구조/위생 축의 과거 실행 계획 문서는 canonical 참조를 제거한 뒤 [`archive/2026-q1/`](archive/2026-q1/README.md) 로 이관했습니다.
6. 아키텍처 축은 [`ARCHITECTURE.md`](ARCHITECTURE.md) 1개 정본과 ADR/마이그레이션 로그 보조 구조로 정리하고, 중복 개요 문서는 archive 로 이관했습니다.
