# 🚀 로컬 CI 검증 가이드

GitHub Actions CI 실패를 방지하기 위한 로컬 검증 프로세스입니다.

## ✅ 빠른 시작

### 1. 의존성 설치
```bash
# 개발 도구 설치
pip install black isort flake8 mypy bandit pytest

# 또는 requirements-dev.txt 사용
pip install -r requirements-dev.txt
```

### 2. 자동 수정 및 검증
```bash
# 포맷팅 자동 수정 + CI 검사
python run_ci_checks.py --fix

# 전체 검사 (테스트 포함)
python run_ci_checks.py --full
```

## 📋 사용 가능한 명령어

### 새로운 CI 검증 도구 (run_ci_checks.py)

| 명령어 | 설명 | 사용 시점 |
|--------|------|----------|
| `python run_ci_checks.py` | 모든 CI 검사 실행 (검사만) | 커밋 전 |
| `python run_ci_checks.py --fix` | 자동 수정 가능한 문제 해결 | 코드 작성 후 |
| `python run_ci_checks.py --quick` | 빠른 검사 (포맷팅, 린팅만) | 개발 중 |
| `python run_ci_checks.py --full` | 전체 검사 + 테스트 | 푸시 전 |
| `python run_ci_checks.py --fix --full` | 자동 수정 + 전체 검사 | PR 생성 전 |

### 기존 도구 (run_tests.py)

| 명령어 | 설명 |
|--------|------|
| `python run_tests.py --format` | Black + isort 포맷팅 |
| `python run_tests.py dev` | 개발용 빠른 테스트 |
| `python run_tests.py ci` | CI 환경 테스트 |

### 개별 도구 직접 실행

```bash
# Black 포맷팅
black newsletter tests web

# isort 임포트 정렬
isort --profile black newsletter tests web

# Flake8 린팅
flake8 newsletter tests web --max-line-length=88 --ignore=E203,W503

# MyPy 타입 체크
mypy newsletter --ignore-missing-imports

# Bandit 보안 검사
bandit -r newsletter web -f txt --skip B104,B110
```

## 🔄 권장 워크플로우

### 1️⃣ 코드 작성 후 (커밋 전)
```bash
# 자동 수정 실행
python run_ci_checks.py --fix

# 변경사항 확인
git diff

# 커밋
git commit -m "feat: 새 기능 추가"
```

### 2️⃣ 푸시 전
```bash
# 전체 검사
python run_ci_checks.py --full

# 문제 없으면 푸시
git push
```

### 3️⃣ PR 생성 전
```bash
# 최종 검증
python run_ci_checks.py --fix --full --verbose
```

## 🛠️ 선택적 설정

### Pre-commit Hooks 설치 (권장)
```bash
# 설치
pre-commit install

# 수동 실행
pre-commit run --all-files
```

### Git Pre-push Hook 설정
```bash
# Windows
git config core.hooksPath .githooks

# 또는 파일 복사
copy .githooks\pre-push .git\hooks\pre-push
```

### Makefile 사용 (Make 설치 필요)
```bash
make format      # 포맷팅
make ci-check    # CI 검사
make ci-fix      # 자동 수정
make push-ready  # 푸시 준비
```

## ❌ 일반적인 CI 실패 원인과 해결

### 1. Black 포맷팅 실패
```bash
python run_ci_checks.py --fix
```

### 2. isort 정렬 실패
```bash
python run_ci_checks.py --fix
```

### 3. Flake8 린팅 오류
```bash
# 오류 확인
flake8 newsletter tests web --max-line-length=88 --ignore=E203,W503

# 주요 오류 타입:
# - F401: 사용하지 않는 import 제거
# - E501: 긴 줄을 88자 이내로 수정
# - E226: 연산자 주변 공백 추가
# - F541: f-string에 placeholder 추가
```

### 4. 테스트 실패
```bash
# 실패한 테스트 확인
pytest -m unit --tb=short -v

# 특정 테스트만 실행
pytest tests/test_specific.py::test_function -v
```

## 📊 CI 검사 항목 체크리스트

- [ ] **Black 포맷팅** - 코드 스타일 일관성
- [ ] **isort 정렬** - import 문 정렬
- [ ] **Flake8 린팅** - 코드 품질 검사
- [ ] **MyPy 타입 체크** - 타입 힌트 검증 (경고만)
- [ ] **Bandit 보안** - 보안 취약점 검사 (경고만)
- [ ] **단위 테스트** - 기능 검증

## 💡 팁

1. **개발 중**: `--quick` 옵션으로 빠른 피드백
2. **커밋 전**: `--fix` 옵션으로 자동 수정
3. **푸시 전**: `--full` 옵션으로 완전한 검증
4. **IDE 설정**: VSCode/PyCharm에서 저장 시 자동 포맷팅 설정 권장

## 🚨 주의사항

- Windows에서 Unicode 관련 경고는 무시해도 됩니다
- MyPy와 Bandit 오류는 CI를 실패시키지 않지만 검토 필요
- 테스트는 `--full` 옵션을 사용할 때만 실행됩니다

## 📚 추가 문서

- [CI/CD 워크플로우 상세](docs/dev/CI_CD_GUIDE.md)
- [GitHub Actions 설정](.github/workflows/main-ci.yml)
- [Pre-commit 설정](.pre-commit-config.yaml)
