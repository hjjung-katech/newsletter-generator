# CI/CD 워크플로우 가이드

## 📋 개요

이 문서는 Newsletter Generator 프로젝트의 CI/CD 파이프라인과 로컬 개발 워크플로우를 설명합니다. GitHub Actions CI 실패를 방지하기 위한 로컬 검증 프로세스를 포함합니다.

## 🔍 CI 파이프라인 구조

### GitHub Actions 검사 항목

1. **코드 품질 검사**
   - Black 포맷팅 체크
   - isort 임포트 정렬 체크
   - Flake8 린팅
   - MyPy 타입 체킹
   - Bandit 보안 스캔

2. **테스트**
   - 단위 테스트 (multi-platform)
   - Mock API 테스트
   - 통합 테스트 (조건부)

## 🛠️ 로컬 개발 워크플로우

### 1. 초기 설정

```bash
# 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Pre-commit hooks 설치 (권장)
pre-commit install

# Git hooks 경로 설정 (선택)
git config core.hooksPath .githooks
```

### 2. 개발 중 사용 명령어

#### 빠른 포맷팅 (기존 방법)
```bash
# Black으로 포맷팅
black newsletter tests web

# isort로 임포트 정렬
isort --profile black newsletter tests web

# 또는 run_tests.py 사용
python run_tests.py --format
```

#### 새로운 CI 검증 도구 사용
```bash
# 모든 CI 검사 실행 (검사만)
python run_ci_checks.py

# 자동 수정 가능한 문제 해결
python run_ci_checks.py --fix

# 빠른 검사 (포맷팅, 린팅만)
python run_ci_checks.py --quick

# 전체 검사 + 테스트
python run_ci_checks.py --full

# 자동 수정 + 전체 검사
python run_ci_checks.py --fix --full
```

#### Makefile 사용 (선택사항)
```bash
# 코드 포맷팅
make format

# CI 검사
make ci-check

# CI 검사 + 자동 수정
make ci-fix

# 푸시 준비 (자동 수정 + 검사)
make push-ready
```

### 3. 권장 워크플로우

#### 커밋 전
```bash
# 1. 코드 포맷팅 및 수정
python run_ci_checks.py --fix

# 2. 변경사항 확인
git diff

# 3. 커밋
git add .
git commit -m "feat: 새로운 기능 추가"
```

#### 푸시 전
```bash
# 전체 CI 검사 실행
python run_ci_checks.py --full

# 문제가 없으면 푸시
git push
```

#### PR 생성 전
```bash
# 상세 모드로 전체 검사
python run_ci_checks.py --full --verbose
```

## 🔧 도구별 상세 설명

### run_ci_checks.py

새롭게 추가된 종합 CI 검증 도구입니다.

**주요 기능:**
- GitHub Actions와 동일한 검사 수행
- 자동 수정 모드 지원
- 단계별 결과 표시
- 실행 시간 측정

**옵션:**
- `--fix`: Black, isort로 자동 수정
- `--quick`: 빠른 검사 (테스트 제외)
- `--full`: 모든 검사 + 테스트
- `--verbose`: 상세 출력

### Pre-commit Hooks

`.pre-commit-config.yaml`에 정의된 자동 검사:
- 코드 포맷팅 (Black, isort)
- 린팅 (Flake8, MyPy)
- 보안 검사 (Bandit, detect-secrets)
- 파일 검사 (YAML, JSON, 큰 파일)

**사용법:**
```bash
# 설치
pre-commit install

# 수동 실행
pre-commit run --all-files

# 특정 파일만 검사
pre-commit run --files newsletter/main.py
```

### Git Pre-push Hook

`.githooks/pre-push`는 푸시 전 자동 검증을 수행합니다.

**설치:**
```bash
# 방법 1: Git hooks 경로 변경
git config core.hooksPath .githooks

# 방법 2: 파일 복사 (Windows)
copy .githooks\pre-push .git\hooks\pre-push

# 방법 3: 파일 복사 (Unix/Mac)
cp .githooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## 📊 CI 실패 해결 가이드

### Black 포맷팅 실패
```bash
# 자동 수정
python run_ci_checks.py --fix
# 또는
black newsletter tests web
```

### isort 정렬 실패
```bash
# 자동 수정
python run_ci_checks.py --fix
# 또는
isort --profile black newsletter tests web
```

### Flake8 린팅 실패
```bash
# 오류 확인
flake8 newsletter tests web --max-line-length=88 --ignore=E203,W503

# 수동으로 각 오류 수정 필요
```

### 테스트 실패
```bash
# 실패한 테스트 확인
pytest -m unit --tb=short -v

# 특정 테스트만 실행
pytest tests/test_specific.py -v
```

## 🔄 CI/CD 파이프라인 흐름

```
1. 로컬 개발
   ↓
2. run_ci_checks.py --fix (커밋 전)
   ↓
3. git commit
   ↓
4. run_ci_checks.py --full (푸시 전)
   ↓
5. git push (pre-push hook 실행)
   ↓
6. GitHub Actions CI 실행
   ↓
7. PR 머지
```

## 💡 팁과 모범 사례

1. **Pre-commit hooks 활용**: 커밋 시 자동으로 코드 품질 검사
2. **CI 검증 도구 활용**: 푸시 전 `run_ci_checks.py --full` 실행
3. **포맷팅 자동화**: VSCode나 PyCharm에서 저장 시 자동 포맷팅 설정
4. **테스트 우선**: 새 기능 추가 시 테스트 먼저 작성
5. **점진적 검사**: 개발 중엔 `--quick`, 푸시 전엔 `--full`

## 🆘 문제 해결

### Windows에서 실행 권한 문제
```bash
# PowerShell 관리자 권한으로 실행
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 패키지 누락
```bash
# 개발 의존성 재설치
pip install -r requirements-dev.txt
```

### Pre-commit 실행 실패
```bash
# 캐시 정리 후 재설치
pre-commit clean
pre-commit install
```

## 📚 참고 자료

- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Flake8 Rules](https://www.flake8rules.com/)
- [Pre-commit](https://pre-commit.com/)
- [GitHub Actions](https://docs.github.com/en/actions)
