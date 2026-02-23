# Newsletter Generator 테스트 가이드

## 📁 개선된 테스트 구조

```
tests/
├── unit_tests/           # 단위 테스트 (외부 의존성 없음)
│   ├── web/             # 웹 관련 단위 테스트
│   ├── test_config_manager.py
│   └── test_scrape_dates.py
├── integration/         # 통합 테스트 (시스템 컴포넌트 간 상호작용)
│   ├── test_cli_integration.py
│   ├── test_web_integration.py
│   └── test_web_api.py
├── e2e/                 # End-to-End 테스트 (웹 서버 필요)
│   ├── test_railway_e2e.py     # ← 이동 필요
│   └── test_deployment.py
├── manual/              # 수동 테스트 (사용자 상호작용 필요)
│   ├── test_api.py      # 웹 서버 필요
│   └── test_api.ps1     # PowerShell 스크립트
├── api_tests/           # 외부 API 테스트
├── deployment/          # 배포 관련 테스트
│   ├── smoke_test.py    # ← 이동 필요
│   └── test_railway.py  # ← 이동 필요
├── test_data/           # 테스트 데이터
├── test_mail.py         # 메일 시스템 테스트
├── run_essential_tests.py  # 필수 테스트 실행기
└── README.md            # 이 파일
```

## 🧪 테스트 카테고리 및 실행 방법

### 1. 단위 테스트 (Unit Tests) ⚡
- **목적**: 개별 함수/클래스의 기능 검증
- **특징**: 빠른 실행 (< 10초), 외부 의존성 없음
- **실행**: `python -m pytest tests/unit_tests/ -v`
- **CI/CD**: 항상 실행

### 2. 통합 테스트 (Integration Tests) 🔗
- **목적**: 컴포넌트 간 상호작용 검증
- **특징**: 시스템 전체 설정 필요, Mock API 사용
- **실행**: `RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/ -v`
- **CI/CD**: PR 시 실행

### 3. E2E 테스트 (End-to-End Tests) 🌐
- **목적**: 전체 사용자 워크플로우 검증
- **특징**: **웹 서버 실행 필수**, 실제 API 호출 가능
- **실행**:
  ```bash
  # 1. 웹 서버 실행 (별도 터미널)
  cd web && python app.py

  # 2. E2E 테스트 실행
  python -m pytest tests/e2e/ -v
  ```
- **CI/CD**: 수동 실행 또는 스테이징 환경

### 4. 배포 테스트 (Deployment Tests) 🚀
- **목적**: 배포 환경 검증
- **특징**: 실제 배포된 서비스에 대한 검증
- **실행**:
  ```bash
  # Railway 배포 후
  python tests/deployment/smoke_test.py --railway
  python tests/deployment/test_railway.py --production
  ```

### 5. 수동 테스트 (Manual Tests) 👤
- **목적**: 사용자 상호작용이나 특별한 환경 필요
- **실행**: `python -m pytest tests/manual/ -v -m manual`

## 🚀 권장 테스트 실행 방법

### 개발 중 (일반적인 경우)
```bash
# 1. 빠른 단위 테스트만
python -m pytest tests/unit_tests/ -v

# 2. 필수 기능 검증
python tests/run_essential_tests.py

# 3. Mock API 포함 전체 테스트 (E2E 제외)
python scripts/devtools/run_tests.py dev
```

### 기능 완성 후 (통합 검증)
```bash
# 1. 통합 테스트 포함
python scripts/devtools/run_tests.py integration

# 2. 웹 서버 실행 후 E2E 테스트
# Terminal 1: cd web && python app.py
# Terminal 2: python -m pytest tests/e2e/ -v
```

### 배포 전 (전체 검증)
```bash
# 실제 API 사용 전체 테스트
python scripts/devtools/run_tests.py integration
```

### 배포 후 (운영 검증)
```bash
# Railway 배포 검증
python tests/deployment/smoke_test.py --railway
```

## 🏷️ 테스트 마커 시스템

프로젝트에서 사용하는 pytest 마커:

- `@pytest.mark.unit`: 단위 테스트
- `@pytest.mark.integration`: 통합 테스트
- `@pytest.mark.e2e`: E2E 테스트 (웹 서버 필요)
- `@pytest.mark.real_api`: 실제 API 호출 필요
- `@pytest.mark.mock_api`: Mock API 사용
- `@pytest.mark.manual`: 수동 테스트
- `@pytest.mark.deployment`: 배포 테스트

## ⚙️ 환경 변수 가이드

### 테스트 실행 제어
- `RUN_REAL_API_TESTS=1`: 실제 API 테스트 활성화
- `RUN_INTEGRATION_TESTS=1`: 통합 테스트 활성화
- `TEST_EMAIL_RECIPIENT`: 테스트 이메일 수신자

### E2E/배포 테스트
- `TEST_BASE_URL`: E2E 테스트 대상 URL (기본: http://localhost:5000)
- `RAILWAY_PRODUCTION_URL`: Railway 배포 URL
- `DEPLOYED_URL`: 일반 배포 URL

### API 키 (실제 API 테스트 시)
- `GEMINI_API_KEY`: Google Gemini API
- `POSTMARK_SERVER_TOKEN`: 이메일 발송
- `SERPER_API_KEY`: 검색 API

## 🔧 테스트 환경 설정

### 웹 서버 의존성 확인
E2E 테스트 실행 전 웹 서버 상태 확인:
```python
def check_web_server(base_url="http://localhost:5000"):
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# E2E 테스트에서 사용
@pytest.fixture(autouse=True)
def ensure_web_server():
    if not check_web_server():
        pytest.skip("웹 서버가 실행되지 않음. 먼저 'cd web && python app.py' 실행 필요")
```

### Mock 설정 개선
ConfigManager 상태 격리:
```python
@pytest.fixture(autouse=True)
def reset_config():
    ConfigManager.reset_for_testing()
    yield
    ConfigManager.reset_for_testing()
```

## 📊 테스트 품질 메트릭

### 성능 기준
- 단위 테스트: < 10초
- 통합 테스트: < 30초
- E2E 테스트: < 2분
- 전체 테스트: < 5분

### 커버리지 목표
- 단위 테스트: > 80%
- 통합 테스트: > 60%
- 전체 커버리지: > 70%

## 🚨 문제 해결 가이드

### E2E 테스트 연결 오류
```
httpx.ConnectError: [WinError 10061] 대상 컴퓨터에서 연결을 거부
```
**해결**: 웹 서버가 실행되지 않음. `cd web && python app.py` 먼저 실행

### API 키 관련 오류
```
External API dependency failed: API key error
```
**해결**: `.env` 파일에 필요한 API 키 설정 또는 Mock 테스트로 전환

### ConfigManager 상태 공유 문제
```python
# 테스트 시작 시 항상 초기화
ConfigManager.reset_for_testing()
```

### 웹 서버 자동 시작 (선택사항)
E2E 테스트용 웹 서버 자동 시작:
```python
@pytest.fixture(scope="session")
def web_server():
    # 웹 서버 프로세스 시작
    import subprocess
    process = subprocess.Popen([sys.executable, "web/app.py"])
    time.sleep(3)  # 서버 시작 대기
    yield
    process.terminate()
```

## 📝 새로운 테스트 작성 가이드

### 1. 적절한 카테고리 선택
- 외부 의존성 없음 → `unit_tests/`
- 컴포넌트 간 상호작용 → `integration/`
- 웹 UI/API 워크플로우 → `e2e/`
- 배포 환경 검증 → `deployment/`

### 2. 마커 및 환경 설정
```python
@pytest.mark.unit
@pytest.mark.mock_api
def test_my_function():
    ConfigManager.reset_for_testing()
    # 테스트 로직
```

### 3. 웹 서버 의존성 처리
```python
@pytest.mark.e2e
def test_web_endpoint():
    if not check_web_server():
        pytest.skip("웹 서버 필요")
    # E2E 테스트 로직
```

이 개선된 구조를 통해 안정적이고 유지보수 가능한 테스트 환경을 제공하며, 개발 단계별로 적절한 테스트를 실행할 수 있습니다.
