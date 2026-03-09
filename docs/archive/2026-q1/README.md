# Archive Index (2026-Q1)

이 디렉터리는 2026-Q1 문서 전수조사에서 active docs tree에서 분리한 이력성 문서를 보관합니다.
운영 정본으로 사용하지 않습니다.

## Archived in This Pass

| Archived Document | Reason | Active Replacement |
|---|---|---|
| [`FIXES_SUMMARY.md`](FIXES_SUMMARY.md) | CI 문제 해결 회고 문서이며 현재 운영 지침과 중복 | [`../../../CHANGELOG.md`](../../../CHANGELOG.md), [`../../dev/CI_CD_GUIDE.md`](../../dev/CI_CD_GUIDE.md) |
| [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) | 현재 파일 구조와 어긋나는 스냅샷 문서 | [`../../dev/LONG_TERM_REPO_STRATEGY.md`](../../dev/LONG_TERM_REPO_STRATEGY.md), [`../../dev/REPO_HYGIENE_POLICY.md`](../../dev/REPO_HYGIENE_POLICY.md) |
| [`MULTI_LLM_IMPLEMENTATION_SUMMARY.md`](MULTI_LLM_IMPLEMENTATION_SUMMARY.md) | 구현 완료 보고서 성격 | [`../../technical/LLM_CONFIGURATION.md`](../../technical/LLM_CONFIGURATION.md), [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) |
| [`REPO_HYGIENE_STATUS_2026-02-24.md`](REPO_HYGIENE_STATUS_2026-02-24.md) | 날짜 박힌 상태 스냅샷 | [`../../dev/REPO_HYGIENE_POLICY.md`](../../dev/REPO_HYGIENE_POLICY.md) |
| [`F14_COMPLETION_REPORT.md`](F14_COMPLETION_REPORT.md) | 이름과 실제 내용이 다른 완료 보고서 | [`../../developer/CENTRALIZED_SETTINGS_GUIDE.md`](../../developer/CENTRALIZED_SETTINGS_GUIDE.md) |
| [`MAIN_INTEGRATION_EXECUTION_PLAN.md`](MAIN_INTEGRATION_EXECUTION_PLAN.md) | 현재 release 실행 기준이 아닌 시점별 통합 계획 | [`../../dev/CI_CD_GUIDE.md`](../../dev/CI_CD_GUIDE.md), [`../../../.github/PULL_REQUEST_TEMPLATE/release_integration.md`](../../../.github/PULL_REQUEST_TEMPLATE/release_integration.md) |
| [`BRANCH_MAIN_GAP_ANALYSIS.md`](BRANCH_MAIN_GAP_ANALYSIS.md) | 과거 `main` 격차 분석 문서 | [`../../dev/CI_CD_GUIDE.md`](../../dev/CI_CD_GUIDE.md) |
| [`REFACTORING_EXECUTION_PLAN.md`](REFACTORING_EXECUTION_PLAN.md) | 시점 고정형 리팩토링 배치 계획 | [`../../dev/LONG_TERM_REPO_STRATEGY.md`](../../dev/LONG_TERM_REPO_STRATEGY.md), [`../../dev/REPO_HYGIENE_POLICY.md`](../../dev/REPO_HYGIENE_POLICY.md) |
| [`UNIFIED_ARCHITECTURE.md`](UNIFIED_ARCHITECTURE.md) | 중복된 아키텍처 개요 문서 | [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md), [`../../technical/adr-0001-architecture-boundaries.md`](../../technical/adr-0001-architecture-boundaries.md) |
| [`CODE_QUALITY.md`](CODE_QUALITY.md) | 현재 게이트 구성과 어긋난 예전 코드 품질 안내 | [`../../dev/CI_CD_GUIDE.md`](../../dev/CI_CD_GUIDE.md), [`../../dev/LOCAL_CI_GUIDE.md`](../../dev/LOCAL_CI_GUIDE.md) |
| [`RR_REQUEST_TEMPLATE.md`](RR_REQUEST_TEMPLATE.md) | GitHub RR 템플릿과 중복된 요청 예시 문서 | [`../../dev/CI_CD_GUIDE.md`](../../dev/CI_CD_GUIDE.md), [`../../../.github/ISSUE_TEMPLATE/review-request.yml`](../../../.github/ISSUE_TEMPLATE/review-request.yml) |
| [`WORKFLOW_TEMPLATES.md`](WORKFLOW_TEMPLATES.md) | contributor workflow 정본과 중복된 템플릿 문서 | [`../../dev/CI_CD_GUIDE.md`](../../dev/CI_CD_GUIDE.md) |
| [`langsmith_setup.md`](langsmith_setup.md) | LangSmith/비용 추적 standalone 가이드가 정본 문서와 중복 | [`../../technical/LLM_CONFIGURATION.md`](../../technical/LLM_CONFIGURATION.md), [`../../reference/environment-variables.md`](../../reference/environment-variables.md) |

## Rollback

이동 롤백이 필요하면 각 파일을 원래 경로로 되돌리고, [`../../DOCUMENT_INVENTORY.md`](../../DOCUMENT_INVENTORY.md) 의 disposition 값을 원복하면 됩니다.
