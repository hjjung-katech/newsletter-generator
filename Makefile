# Newsletter Generator - Makefile
# 개발 워크플로우 자동화를 위한 Makefile

.PHONY: help format lint test ci-check ci-fix clean install pre-commit

# Python 실행 파일 설정
PYTHON := python
PIP := $(PYTHON) -m pip

# 디렉토리 설정
SRC_DIRS := newsletter tests web

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
	$(PYTHON) -m flake8 $(SRC_DIRS) --max-line-length=88 --ignore=E203,W503
	$(PYTHON) -m mypy newsletter --ignore-missing-imports || true
	$(PYTHON) -m bandit -r newsletter web -f txt --skip B104,B110 || true

test: ## 단위 테스트 실행
	@echo "🧪 단위 테스트 실행 중..."
	MOCK_MODE=true $(PYTHON) -m pytest -m unit --tb=short

test-all: ## 모든 테스트 실행
	@echo "🧪 전체 테스트 실행 중..."
	$(PYTHON) run_tests.py ci

test-coverage: ## 커버리지 포함 테스트
	@echo "📊 커버리지 측정 중..."
	MOCK_MODE=true $(PYTHON) -m pytest -m unit --cov=newsletter --cov-report=html --cov-report=term

ci-check: ## CI 검사 실행 (GitHub Actions와 동일)
	@echo "🚀 CI 검사 실행 중..."
	$(PYTHON) run_ci_checks.py

ci-fix: ## CI 검사 + 자동 수정
	@echo "🔧 CI 검사 및 자동 수정 중..."
	$(PYTHON) run_ci_checks.py --fix

ci-full: ## 전체 CI 검사 (테스트 포함)
	@echo "🚀 전체 CI 검사 실행 중..."
	$(PYTHON) run_ci_checks.py --full

pre-commit: ## Pre-commit hooks 설치
	@echo "🔗 Pre-commit hooks 설치 중..."
	pre-commit install
	@echo "✅ Pre-commit hooks 설치 완료!"

pre-commit-run: ## Pre-commit 수동 실행
	@echo "🔍 Pre-commit 검사 실행 중..."
	pre-commit run --all-files

clean: ## 캐시 및 임시 파일 정리
	@echo "🧹 정리 중..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf .pytest_cache/ 2>/dev/null || true
	rm -rf .mypy_cache/ 2>/dev/null || true
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
	$(PYTHON) run_tests.py --format

win-test: ## Windows용 테스트
	$(PYTHON) run_tests.py dev
endif
