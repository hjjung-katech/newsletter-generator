# Tasks

## TASK-C — requirements-e2e.txt + hygiene allowlist + E2E setup docs
- [x] requirements-e2e.txt 신규 작성 (playwright>=1.40.0 pinned)
- [x] scripts/repo_hygiene_policy.json: requirements-e2e.txt allowlist 추가
- [x] docs/setup/LOCAL_SETUP.md: Section 14 "E2E 스모크 테스트 로컬 실행" 추가

## TASK-B — Register e2e-smoke as required status check + doc update
- [x] GitHub branch protection: added `e2e-smoke` to main required checks (via gh API)
- [x] .github/workflows/README.md: added `e2e-smoke` to required checks list
- [x] docs/dev/CI_CD_GUIDE.md: updated count 12→13, added `e2e-smoke` to PR gate list

## TASK-A — Pre-existing failing tests: add explicit skip markers
- [x] tests/api_tests/test_article_filter_integration.py::test_cli_integration — skip (news_summarize removed)
- [x] tests/unit_tests/test_llm.py::TestLLMSystem::test_api_keys_configuration — skip (requires GEMINI_API_KEY)
- [x] tests/unit_tests/test_llm.py::TestLLMSystem::test_provider_availability — skip (requires API keys)
- [x] tests/unit_tests/test_llm.py::TestLLMSystem::test_llm_instance_creation — skip (requires API keys)
- [x] tests/unit_tests/test_llm.py::TestLLMSystem::test_fallback_mechanism — skip (requires API keys)
- [x] tests/unit_tests/test_llm_providers.py::TestLLMProviders::test_all_task_llm_creation — skip (requires API keys)
- [x] tests/unit_tests/test_llm_providers.py::TestLLMProviders::test_provider_distribution — skip (requires API keys)
- [x] tests/unit_tests/test_llm_providers.py::TestLLMProviders::test_fallback_mechanism_detailed — skip (requires API keys)
- [x] tests/contract/test_dev_entrypoint_consistency.py::test_active_docs_point_to_python_entrypoint_and_avoid_fixed_clone_paths — skip ("thin wrapper" missing from README)
- 제약: 소스 코드 수정 없음, 테스트 파일만 수정

## Prompt C — generation contract 테스트
- [x] tests/contract/test_generation_routes_contract.py 신규 작성
- 대상 경로 4개:
    - POST /generate → 202 (first call)
    - POST /generate → 202 + dedup flag (duplicate)
    - POST /generate → 400 (missing required field)
    - POST /schedule/<id>/run → 200 (immediate execution)
- 제약: 신규 파일만, 소스 코드 및 기존 테스트 파일 수정 없음
- 패턴 참조: tests/contract/test_web_email_routes_contract.py

## Lessons 정비
- [x] tasks/lessons.md 에 LESSON-002 (test/ prefix 불허) 추가
- [x] tasks/lessons.md 에 LESSON-003 (__init__.py 필수) 추가
- [x] tasks/lessons.md 에 LESSON-006 (playwright 단독 사용) 추가
- [x] tasks/lessons.md 에 LESSON-007 (CI requirements.txt 방식) 추가

## P1-A — .env.example 가독성 개선
- [x] .env.example 기능별 블록 헤더 추가 및 Required/Optional 인라인 주석 추가
- [x] docs/reference/environment-variables.md 섹션명 정렬 및 SERPER_API_KEY 필수 여부 수정

## P1-C — shell size soft-gate CI job
- [x] scripts/measure_module_size.py 신규 작성 (freeze 모듈 5개 LOC/complexity 측정)
- [x] .github/workflows/shell-size-gate.yml 신규 작성 (PR comment + Step Summary)

## P1-B — newsletter_core.public mypy 활성화
- [x] pyproject.toml: newsletter_core.public.* ignore_errors = false 전환
- [x] newsletter_core/public/generation.py: 타입 annotation 2건 수정

## P1-D — Playwright E2E 스모크 테스트 추가
- [x] tests/e2e/conftest.py 신규 작성 (live_server + browser + page fixtures)
- [x] tests/e2e/test_smoke.py 신규 작성 (GET /health, GET / 2개 스모크 테스트)
- [x] .github/workflows/e2e-smoke.yml 신규 작성 (blocking CI gate)
- [x] workflow count 업데이트 (8→9): README.md, CI_CD_GUIDE.md, contract test
