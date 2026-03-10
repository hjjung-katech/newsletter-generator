# Newsletter Generator - Makefile
# 개발 워크플로우 자동화를 위한 Makefile

.PHONY: help bootstrap doctor print-python print-venv check check-full format format-check lint architecture-check architecture-baseline test test-quick test-full test-nightly preflight-release validate-ci-manifest validate-scheduler-manifest validate-runtime-bootstrap-manifest apply-pr-metadata ci-check ci-fix clean clean-caches clean-local clean-venv install pre-commit pre-commit-run skill-ci-gate skill-docs-and-config-consistency skill-newsletter-smoke skill-web-smoke skill-scheduler-debug skill-release-integration skills-check docs-check repo-audit repo-audit-strict runtime-ascii-guard legacy-web-types-guard ops-safety-check ops-safety-smoke ops-safety-report build-web-exe windows-release-artifacts verify-windows-artifact-checksum support-bundle windows-sign-exe validate-windows-release-artifacts windows-update-manifest windows-ci-burnin-report github-windows-release-controls

# 실행 경로/인터프리터 설정
EXPECTED_CWD ?= /Users/hojungjung/development/newsletter-generator
PROJECT_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
LOCAL_DIR ?= $(PROJECT_ROOT)/.local
ARTIFACTS_DIR ?= $(LOCAL_DIR)/artifacts
REPO_AUDIT_DIR ?= $(ARTIFACTS_DIR)/repo-audit
WINDOWS_CI_BURNIN_REPORT ?= $(ARTIFACTS_DIR)/windows-ci-burnin.json
WINDOWS_RELEASE_CONTROLS_REPORT ?= $(ARTIFACTS_DIR)/windows-release-controls.json
COVERAGE_DIR ?= $(LOCAL_DIR)/coverage
DEBUG_DIR ?= $(LOCAL_DIR)/debug_files
NEWSLETTER_DEBUG_DIR ?= $(DEBUG_DIR)
DEFAULT_VENV_DIR ?= $(LOCAL_DIR)/venv
LEGACY_VENV_DIR ?= $(PROJECT_ROOT)/.venv
BOOTSTRAP_VENV_DIR ?= $(DEFAULT_VENV_DIR)
VENV_DIR ?= $(DEFAULT_VENV_DIR)
ifeq ($(origin VENV_DIR), file)
  ifeq ($(wildcard $(DEFAULT_VENV_DIR)/bin/python)$(wildcard $(DEFAULT_VENV_DIR)/Scripts/python.exe),)
    ifneq ($(wildcard $(LEGACY_VENV_DIR)/bin/python)$(wildcard $(LEGACY_VENV_DIR)/Scripts/python.exe),)
      VENV_DIR := $(LEGACY_VENV_DIR)
    endif
  endif
endif
BOOTSTRAP_VENV_PYTHON := $(if $(wildcard $(BOOTSTRAP_VENV_DIR)/Scripts/python.exe),$(BOOTSTRAP_VENV_DIR)/Scripts/python.exe,$(BOOTSTRAP_VENV_DIR)/bin/python)
VENV_PYTHON := $(if $(wildcard $(VENV_DIR)/Scripts/python.exe),$(VENV_DIR)/Scripts/python.exe,$(VENV_DIR)/bin/python)
PYTHON ?= $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),python3)
PIP := $(PYTHON) -m pip
export NEWSLETTER_DEBUG_DIR

# 디렉토리 설정
SRC_DIRS := newsletter tests web scripts apps newsletter_core

help: ## 도움말 표시
	@echo "Newsletter Generator - 개발 명령어"
	@echo "=================================="
	@echo ""
	@echo "사용 가능한 명령어:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-15s %s\n", $$1, $$2}'
	@echo ""
	@echo "예시:"
	@echo "  make format      # 코드 포맷팅"
	@echo "  make ci-check    # CI 검사 실행"
	@echo "  make test        # 테스트 실행"

bootstrap: ## 로컬 가상환경/의존성/훅 설치
	@echo "🧱 로컬 개발 환경 bootstrap 중..."
	python3 -m venv $(BOOTSTRAP_VENV_DIR)
	$(BOOTSTRAP_VENV_PYTHON) -m pip install --upgrade pip
	$(BOOTSTRAP_VENV_PYTHON) -m pip install -r requirements.txt
	$(BOOTSTRAP_VENV_PYTHON) -m pip install -r requirements-dev.txt
	$(BOOTSTRAP_VENV_PYTHON) -m pre_commit install
	@echo "✅ bootstrap 완료"

doctor: ## 작업 경로/인터프리터 전제 조건 검증
	@echo "🩺 환경 점검 중..."
	@current_dir="$$(pwd)"; \
	if [ "$$current_dir" != "$(EXPECTED_CWD)" ]; then \
		echo "❌ 잘못된 작업 경로: $$current_dir"; \
		echo "   올바른 경로: $(EXPECTED_CWD)"; \
		exit 1; \
	fi
	@repo_root="$$(git rev-parse --show-toplevel 2>/dev/null || true)"; \
	if [ "$$repo_root" != "$(EXPECTED_CWD)" ]; then \
		echo "❌ Git 루트 불일치: $$repo_root"; \
		echo "   예상 루트: $(EXPECTED_CWD)"; \
		exit 1; \
	fi
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		echo "❌ 가상환경 Python 없음: $(VENV_PYTHON)"; \
		echo "   기본 경로는 $(DEFAULT_VENV_DIR) 입니다. 먼저 'make bootstrap'을 실행하세요."; \
		exit 1; \
	fi
	@echo "✅ 환경 점검 통과 (PYTHON=$(PYTHON), VENV_DIR=$(VENV_DIR))"

print-python: ## 현재 선택된 Python 인터프리터 경로 출력
	@echo "$(PYTHON)"

print-venv: ## 현재 선택된 가상환경 디렉터리 경로 출력
	@echo "$(VENV_DIR)"

check: doctor test-quick docs-check skills-check ## 표준 로컬 게이트
	@echo "✅ check 완료"

check-full: doctor test-full docs-check skills-check ops-safety-check ## PR 전 전체 게이트
	@echo "✅ check-full 완료"

install: ## 의존성 설치
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

format: ## 코드 포맷팅 (Black + isort)
	@echo "🎨 코드 포맷팅 중..."
	$(PYTHON) -m black $(SRC_DIRS)
	$(PYTHON) -m isort --profile black $(SRC_DIRS)
	@echo "✅ 포맷팅 완료!"

format-check: ## 포맷팅 검사만 (수정하지 않음)
	@echo "🔍 포맷팅 검사 중..."
	$(PYTHON) -m black --check --diff $(SRC_DIRS)
	$(PYTHON) -m isort --check-only --diff --profile black $(SRC_DIRS)

lint: ## 린팅 실행 (flake8 + mypy + bandit)
	@echo "🔍 린팅 검사 중..."
	$(PYTHON) -m flake8 $(SRC_DIRS) --max-line-length=88 --ignore=E203,W503,E501
	$(PYTHON) -m mypy newsletter --ignore-missing-imports
	$(PYTHON) -m bandit -r newsletter web -f txt --skip B104,B110

architecture-check: ## 아키텍처 경계/사이클 검사
	@echo "🏗️ 아키텍처 경계 검사 실행 중..."
	$(PYTHON) scripts/architecture/check_import_boundaries.py --mode ratchet
	$(PYTHON) scripts/architecture/check_import_cycles.py

architecture-baseline: ## 현재 import 위반을 baseline으로 갱신
	@echo "🧭 아키텍처 baseline 갱신 중..."
	$(PYTHON) scripts/architecture/check_import_boundaries.py --update-baseline

test: ## 단위 테스트 실행
	@echo "🧪 단위 테스트 실행 중..."
	MOCK_MODE=true $(PYTHON) -m pytest -m unit --tb=short

preflight-release: ## 릴리즈 사전 점검 (기준선/필수 파일/도구)
	@echo "🛫 Release preflight 실행 중..."
	$(PYTHON) scripts/release_preflight.py

build-web-exe: ## Windows EXE canonical build entrypoint
	@echo "🪟 Windows EXE 빌드 실행 중..."
	$(PYTHON) scripts/devtools/build_web_exe_enhanced.py

windows-release-artifacts: ## Generate release metadata + SHA256 for Windows artifact
	@echo "📦 Windows 릴리즈 메타데이터/체크섬 생성 중..."
	$(PYTHON) scripts/devtools/generate_windows_release_artifacts.py --artifact dist/newsletter_web.exe --output-dir dist --target-os windows-x64

verify-windows-artifact-checksum: ## Verify SHA256 for EXE/metadata/support bundle artifacts
	@echo "🔐 Windows 아티팩트 체크섬 검증 중..."
	@ARTIFACT_ARGS="--artifact dist/newsletter_web.exe --artifact dist/release-metadata.json --artifact dist/support-bundle.zip"; \
	if [ -f dist/update-manifest.json ]; then \
		ARTIFACT_ARGS="$$ARTIFACT_ARGS --artifact dist/update-manifest.json"; \
	fi; \
	$(PYTHON) scripts/devtools/verify_windows_artifact_checksum.py $$ARTIFACT_ARGS --checksum-file dist/SHA256SUMS.txt

support-bundle: ## Create sanitized support bundle for customer troubleshooting
	@echo "🧰 지원용 진단 번들 생성 중..."
	$(PYTHON) scripts/devtools/create_support_bundle.py --artifact dist/newsletter_web.exe --dist-dir dist --checksum-file dist/SHA256SUMS.txt --output dist/support-bundle.zip

windows-sign-exe: ## Sign Windows exe using OV certificate thumbprint
	@echo "✍️ Windows EXE 코드서명 실행 중..."
	pwsh ./scripts/devtools/sign_windows_exe.ps1 -ExePath "dist\\newsletter_web.exe" -CertSha1 "$(WINDOWS_OV_CERT_SHA1)" $(if $(REQUIRE_SIGNATURE),-RequireSignature,)

validate-windows-release-artifacts: ## Validate release metadata/checksum/support bundle package
	@echo "🧪 Windows 릴리즈 아티팩트 검증 중..."
	$(PYTHON) scripts/devtools/validate_windows_release_artifacts.py --dist-dir dist $(if $(REQUIRE_SIGNING),--require-signing,) $(if $(REQUIRE_UPDATE_MANIFEST),--require-update-manifest,)

windows-update-manifest: ## Generate update-manifest.json (WINDOWS_UPDATE_BASE_URL required)
	@echo "🔄 업데이트 매니페스트 생성 중..."
	@if [ -z "$(WINDOWS_UPDATE_BASE_URL)" ]; then \
		echo "❌ WINDOWS_UPDATE_BASE_URL 환경변수가 필요합니다."; \
		exit 1; \
	fi
	$(PYTHON) scripts/devtools/generate_windows_update_manifest.py --metadata dist/release-metadata.json --output dist/update-manifest.json --base-url "$(WINDOWS_UPDATE_BASE_URL)" --checksum-file dist/SHA256SUMS.txt

windows-ci-burnin-report: ## Measure latest Windows CI burn-in success rate
	@echo "📈 Windows CI burn-in 리포트 생성 중..."
	$(PYTHON) scripts/devtools/windows_ci_burnin_report.py --workflow "Main CI Pipeline" --branch main --limit 10 --min-success-rate 95 --output $(WINDOWS_CI_BURNIN_REPORT)

github-windows-release-controls: ## Verify GitHub release controls (branch protection/vars/secrets)
	@echo "🧭 GitHub Windows release control 점검 중..."
	$(PYTHON) scripts/devtools/check_github_windows_release_controls.py --repo hjjung-katech/newsletter-generator --output $(WINDOWS_RELEASE_CONTROLS_REPORT)

test-quick: preflight-release ## 빠른 게이트 (5분 이내 목표: 포맷/린트/핵심 단위)
	@echo "⚡ Quick 게이트 실행 중..."
	$(PYTHON) run_ci_checks.py --quick
	@if git diff --name-only --cached | grep -E '^(newsletter|web)/.*\.py$$' >/dev/null; then \
		MOCK_MODE=true TESTING=1 OPENAI_API_KEY=test-key SERPER_API_KEY=test-key GEMINI_API_KEY=test-key ANTHROPIC_API_KEY=test-key POSTMARK_SERVER_TOKEN=dummy-token EMAIL_SENDER=test@example.com $(PYTHON) -m pytest -m "unit" --maxfail=1 --tb=short; \
	else \
		echo "ℹ️  staged 런타임 Python 변경이 없어 quick pytest를 건너뜁니다."; \
	fi

test-full: preflight-release ## PR 게이트 (전체 CI + 테스트)
	@echo "🚦 Full 게이트 실행 중..."
	$(PYTHON) run_ci_checks.py --full

test-nightly: ## 야간 장기 시나리오 (스케줄/종료 회귀)
	@echo "🌙 Nightly 게이트 실행 중..."
	MOCK_MODE=true $(PYTHON) -m pytest tests/integration/test_schedule_execution.py tests/integration/test_graceful_shutdown.py --tb=short


validate-ci-manifest: ## release/ci-platform 변경 범위(manifest) 검증
	@echo "🧭 CI manifest 검증 실행 중..."
	$(PYTHON) scripts/validate_release_manifest.py --manifest .release/manifests/release-ci-platform.txt --source staged

validate-scheduler-manifest: ## release/scheduler-reliability 변경 범위(manifest) 검증
	@echo "🧭 Scheduler manifest 검증 실행 중..."
	$(PYTHON) scripts/validate_release_manifest.py --manifest .release/manifests/release-scheduler-reliability.txt --source staged

validate-runtime-bootstrap-manifest: ## runtime-binary bootstrap 변경 범위(manifest) 검증
	@echo "🧭 Runtime bootstrap manifest 검증 실행 중..."
	$(PYTHON) scripts/validate_release_manifest.py --manifest .release/manifests/release-runtime-binary-bootstrap.txt --source staged

apply-pr-metadata: ## PR 라벨/리뷰어 적용 (PR=<number>, REVIEWERS=<a,b> or .release/reviewer_roles.json)
	@echo "🏷️ PR metadata 적용 중..."
	$(PYTHON) scripts/apply_pr_metadata.py --pr $(PR) --reviewers "$(REVIEWERS)"

test-all: ## 모든 테스트 실행
	@echo "🧪 전체 테스트 실행 중..."
	$(PYTHON) scripts/devtools/run_tests.py ci

test-coverage: ## 커버리지 포함 테스트
	@echo "📊 커버리지 측정 중..."
	MOCK_MODE=true $(PYTHON) -m pytest -m unit --cov=newsletter --cov=newsletter_core --cov=web --cov-report=html:$(COVERAGE_DIR)/htmlcov --cov-report=term

ci-check: ## CI 검사 실행 (GitHub Actions와 동일)
	@echo "🚀 CI 검사 실행 중..."
	$(PYTHON) run_ci_checks.py

ci-fix: ## CI 검사 + 자동 수정
	@echo "🔧 CI 검사 및 자동 수정 중..."
	$(PYTHON) run_ci_checks.py --fix

ci-full: ## 전체 CI 검사 (테스트 포함)
	@echo "🚀 전체 CI 검사 실행 중..."
	$(PYTHON) run_ci_checks.py --full

skill-ci-gate: ## Skill: ci-gate
	@echo "🧠 Skill ci-gate 실행 중..."
	$(PYTHON) run_ci_checks.py --fix --full

skill-docs-and-config-consistency: ## Skill: docs-and-config-consistency
	@echo "🧠 Skill docs-and-config-consistency 검증 중..."
	@! rg -nP 'SENDGRID_API_KEY|(?<!POSTMARK_)FROM_EMAIL=|POSTMARK_TOKEN|POSTMARK_API_TOKEN' README.md docs/setup web/.env.example web/requirements.txt

skill-newsletter-smoke: ## Skill: newsletter-smoke
	@echo "🧠 Skill newsletter-smoke 실행 중..."
	MOCK_MODE=true TESTING=1 OPENAI_API_KEY=test-key SERPER_API_KEY=test-key GEMINI_API_KEY=test-key ANTHROPIC_API_KEY=test-key POSTMARK_SERVER_TOKEN=dummy-token EMAIL_SENDER=test@example.com $(PYTHON) -c "from unittest.mock import patch; from newsletter_core.public.generation import GenerateNewsletterRequest, generate_newsletter; sample='<html><head><title>Smoke</title></head><body>ok</body></html>'; info={'step_times': {'collect': 0.1}, 'total_time': 0.2}; p1=patch('newsletter_core.public.generation.graph.generate_newsletter', return_value=(sample, 'success')); p2=patch('newsletter_core.public.generation.graph.get_last_generation_info', return_value=info); p1.start(); p2.start(); r=generate_newsletter(GenerateNewsletterRequest(keywords='AI', period=7)); p2.stop(); p1.stop(); assert r['status']=='success'; assert r['title']=='Smoke'; assert '<html' in r['html_content'].lower(); print('newsletter-smoke: ok')"

skill-web-smoke: ## Skill: web-smoke
	@echo "🧠 Skill web-smoke 실행 중..."
	MOCK_MODE=true TESTING=1 OPENAI_API_KEY=test-key SERPER_API_KEY=test-key GEMINI_API_KEY=test-key ANTHROPIC_API_KEY=test-key POSTMARK_SERVER_TOKEN=dummy-token EMAIL_SENDER=test@example.com $(PYTHON) -m pytest tests/test_web_api.py -q

skill-scheduler-debug: ## Skill: scheduler-debug
	@echo "🧠 Skill scheduler-debug 실행 중..."
	MOCK_MODE=true TESTING=1 $(PYTHON) -m pytest tests/integration/test_schedule_execution.py tests/unit_tests/test_schedule_time_sync.py -q

skill-release-integration: ## Skill: release-integration
	@echo "🧠 Skill release-integration 실행 중..."
	$(PYTHON) scripts/release_preflight.py
	$(PYTHON) scripts/validate_release_manifest.py --manifest .release/manifests/release-ci-platform.txt --source staged
	$(PYTHON) scripts/validate_release_manifest.py --manifest .release/manifests/release-scheduler-reliability.txt --source staged
	$(PYTHON) scripts/validate_release_manifest.py --manifest .release/manifests/release-runtime-binary-bootstrap.txt --source staged
	$(PYTHON) scripts/generate_ops_safety_report.py

skills-check: skill-docs-and-config-consistency skill-newsletter-smoke skill-web-smoke skill-scheduler-debug ## Run core skills verification
	@echo "✅ skills-check 완료"

ops-safety-check: ## Run operational-safety required tests
	@echo "🛡️ Ops-safety 게이트 실행 중..."
	MOCK_MODE=true TESTING=1 OPENAI_API_KEY=test-key SERPER_API_KEY=test-key GEMINI_API_KEY=test-key ANTHROPIC_API_KEY=test-key POSTMARK_SERVER_TOKEN=dummy-token EMAIL_SENDER=test@example.com $(PYTHON) -m pytest tests/unit_tests/test_config_import_side_effects.py -q
	MOCK_MODE=true TESTING=1 OPENAI_API_KEY=test-key SERPER_API_KEY=test-key GEMINI_API_KEY=test-key ANTHROPIC_API_KEY=test-key POSTMARK_SERVER_TOKEN=dummy-token EMAIL_SENDER=test@example.com $(PYTHON) -m pytest tests/test_web_api.py -q
	RUN_INTEGRATION_TESTS=1 MOCK_MODE=true TESTING=1 OPENAI_API_KEY=test-key SERPER_API_KEY=test-key GEMINI_API_KEY=test-key ANTHROPIC_API_KEY=test-key POSTMARK_SERVER_TOKEN=dummy-token EMAIL_SENDER=test@example.com $(PYTHON) -m pytest tests/integration/test_schedule_execution.py -q
	MOCK_MODE=true TESTING=1 OPENAI_API_KEY=test-key SERPER_API_KEY=test-key GEMINI_API_KEY=test-key ANTHROPIC_API_KEY=test-key POSTMARK_SERVER_TOKEN=dummy-token EMAIL_SENDER=test@example.com $(PYTHON) -m pytest tests/unit_tests/test_schedule_time_sync.py -q
	MOCK_MODE=true TESTING=1 OPENAI_API_KEY=test-key SERPER_API_KEY=test-key GEMINI_API_KEY=test-key ANTHROPIC_API_KEY=test-key POSTMARK_SERVER_TOKEN=dummy-token EMAIL_SENDER=test@example.com $(PYTHON) -m pytest tests/contract/test_web_email_routes_contract.py -q
	@echo "✅ ops-safety-check 완료"

ops-safety-smoke: ## Run deployed idempotency/outbox smoke checks (BASE_URL required)
	@echo "🧪 Ops-safety smoke 실행 중..."
	@if [ -z "$${BASE_URL}" ]; then \
		echo "❌ BASE_URL 환경변수가 필요합니다. 예: BASE_URL=https://your-app.railway.app make ops-safety-smoke"; \
		exit 1; \
	fi
	$(PYTHON) scripts/ops_safety_smoke.py --base-url "$${BASE_URL}" $${SMOKE_ARGS:-}
	@echo "✅ ops-safety-smoke 완료"

ops-safety-report: ## Generate operational safety release report
	@echo "📝 Ops-safety 리포트 생성 중..."
	$(PYTHON) scripts/generate_ops_safety_report.py
	@echo "✅ ops-safety-report 완료"

docs-check: ## Markdown 링크/스타일 무결성 검사
	@echo "🧾 문서 품질 검사 중..."
	$(PYTHON) scripts/check_markdown_links.py
	$(PYTHON) scripts/check_markdown_style.py
	@echo "✅ docs-check 완료"

repo-audit: ## 루트 인벤토리/Repo hygiene soft gate 리포트 생성
	@echo "🧹 Repo audit 실행 중..."
	$(PYTHON) scripts/repo_audit.py --policy scripts/repo_hygiene_policy.json --output-dir $(REPO_AUDIT_DIR) --check-policy
	@echo "✅ repo-audit 완료 ($(REPO_AUDIT_DIR))"

repo-audit-strict: ## 루트 인벤토리/Repo hygiene strict gate 리허설
	@echo "🧱 Repo audit strict 실행 중..."
	$(PYTHON) scripts/repo_audit.py --policy scripts/repo_hygiene_policy.json --output-dir $(REPO_AUDIT_DIR) --check-policy --strict
	@echo "✅ repo-audit-strict 완료 ($(REPO_AUDIT_DIR))"

runtime-ascii-guard: ## Ensure runtime print/logger literals stay ASCII-safe
	@echo "🔡 Runtime ASCII 출력 가드 실행 중..."
	$(PYTHON) scripts/devtools/check_runtime_ascii_output.py
	@echo "✅ runtime-ascii-guard 완료"

legacy-web-types-guard: ## Ensure only runtime compatibility files mention legacy web_types refs
	@echo "🧭 Legacy web_types 참조 가드 실행 중..."
	$(PYTHON) scripts/devtools/check_legacy_web_types_paths.py
	@echo "✅ legacy-web-types-guard 완료"

pre-commit: ## Pre-commit hooks 설치
	@echo "🔗 Pre-commit hooks 설치 중..."
	pre-commit install
	@echo "✅ Pre-commit hooks 설치 완료!"

pre-push-hook: ## Local pre-push hook 설치
	@echo "🔗 Pre-push hook 설치 중..."
	./scripts/devtools/setup_pre_push_hook.sh
	@echo "✅ Pre-push hook 설치 완료!"

setup-local-git: pre-commit pre-push-hook ## 로컬 Git 훅(커밋/푸시) 설치
	@echo "✅ 로컬 Git hook 설치 완료!"

pre-commit-run: ## Pre-commit 수동 실행
	@echo "🔍 Pre-commit 검사 실행 중..."
	pre-commit run --all-files

clean-caches: ## 재생성 가능한 캐시/coverage 정리
	@echo "🧽 캐시 정리 중..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d \( -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" -o -name ".hypothesis" -o -name ".tox" -o -name ".nox" -o -name ".pytype" \) -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -f coverage.xml 2>/dev/null || true
	rm -rf artifacts/ 2>/dev/null || true
	rm -rf coverage_html_report/ 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf $(ARTIFACTS_DIR)/ 2>/dev/null || true
	rm -rf $(COVERAGE_DIR)/ 2>/dev/null || true
	@echo "✅ 캐시 정리 완료!"

clean-local: clean-caches ## .local scratch 산출물 정리 (output/과 venv 제외)
	@echo "🧹 로컬 scratch 정리 중..."
	rm -rf $(DEBUG_DIR)/ 2>/dev/null || true
	@echo "✅ 로컬 scratch 정리 완료!"

clean-venv: ## 로컬 가상환경 정리 (.local/venv + legacy .venv)
	@echo "🗑️ 가상환경 정리 중..."
	rm -rf $(DEFAULT_VENV_DIR) 2>/dev/null || true
	rm -rf $(LEGACY_VENV_DIR) 2>/dev/null || true
	@echo "✅ 가상환경 정리 완료!"

clean: clean-local ## 캐시 및 임시 파일 정리
	@echo "🧹 추가 빌드 산출물 정리 중..."
	rm -rf dist/ build/ *.egg-info 2>/dev/null || true
	@echo "✅ 정리 완료!"

# 워크플로우 조합
prepare: format lint ## 커밋 준비 (포맷팅 + 린팅)
	@echo "✅ 커밋 준비 완료!"

push-ready: ci-fix ci-check ## 푸시 준비 (자동 수정 + CI 검사)
	@echo "✅ 푸시 준비 완료!"

# Windows 전용 명령어
ifeq ($(OS),Windows_NT)
win-format: ## Windows용 포맷팅
	$(PYTHON) scripts/devtools/run_tests.py --format

win-test: ## Windows용 테스트
	$(PYTHON) scripts/devtools/run_tests.py dev
endif
