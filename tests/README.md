# Newsletter Generator 테스트 가이드

## 📁 테스트 구조

```
tests/
├── unit_tests/           # 단위 테스트
│   ├── web/             # 웹 관련 단위 테스트
│   ├── test_config_manager.py
│   └── test_scrape_dates.py
├── integration/         # 통합 테스트
│   ├── test_cli_integration.py
│   ├── test_web_integration.py
│   └── test_web_api.py
├── manual/              # 수동 테스트
│   ├── test_api.py      # 웹 서버 필요
│   └── test_api.ps1     # PowerShell 스크립트
├── api_tests/           # API 테스트 (외부 API 호출)
├── test_data/           # 테스트 데이터
├── test_mail.py         # 메일 시스템 테스트
├── run_essential_tests.py  # 필수 테스트 실행기
└── README.md            # 이 파일
```

## 🧪 테스트 카테고리

### 1. 단위 테스트 (Unit Tests)
- **목적**: 개별 함수/클래스의 기능 검증
- **특징**: 빠른 실행, 외부 의존성 없음
- **실행**: `python -m pytest tests/unit_tests/ -v`

#### 주요 테스트:
- `test_config_manager.py`: ConfigManager 클래스 기능
- `test_scrape_dates.py`: 날짜 처리 기능
- `web/`: 웹 관련 단위 테스트

### 2. 통합 테스트 (Integration Tests)
- **목적**: 컴포넌트 간 상호작용 검증
- **특징**: 시스템 전체 설정 필요
- **실행**: `RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/ -v`

### 3. 수동 테스트 (Manual Tests)
- **목적**: 사용자 상호작용이나 특별한 환경 필요
- **특징**: 웹 서버 실행, 실제 API 호출 등
- **실행**: `python -m pytest tests/manual/ -v -m manual`

### 4. API 테스트
- **목적**: 외부 API 연동 검증
- **특징**: 실제 API 키 필요, 네트워크 연결 필요
- **실행**: `RUN_REAL_API_TESTS=1 python -m pytest tests/api_tests/ -v`

## 🚀 테스트 실행 방법

### 기본 테스트 (권장)
```bash
# 단위 테스트만 실행 (가장 빠름)
python -m pytest tests/unit_tests/ -v

# 필수 테스트만 실행
python tests/run_essential_tests.py

# 모든 단위 테스트 + 메일 테스트
python -m pytest tests/ -m "not manual and not real_api" -v
```

### 전체 테스트
```bash
# DEV 환경 (Mock API 사용)
python run_tests.py dev

# FULL 환경 (실제 API 사용, API 키 필요)
python run_tests.py full
```

### 특정 테스트
```bash
# ConfigManager만 테스트
python -m pytest tests/unit_tests/test_config_manager.py -v

# 메일 시스템만 테스트
python -m pytest tests/test_mail.py -v

# 수동 테스트 (웹 서버 필요)
python -m pytest tests/manual/ -v -m manual
```

## 🏷️ 테스트 마커

프로젝트에서 사용하는 pytest 마커:

- `@pytest.mark.real_api`: 실제 API 호출 필요
- `@pytest.mark.mock_api`: Mock API 사용
- `@pytest.mark.integration`: 통합 테스트
- `@pytest.mark.manual`: 수동 테스트 (웹 서버 등 필요)

## ⚙️ 환경 변수

테스트 실행 시 사용하는 환경 변수:

- `RUN_REAL_API_TESTS=1`: 실제 API 테스트 활성화
- `RUN_INTEGRATION_TESTS=1`: 통합 테스트 활성화
- `TEST_EMAIL_RECIPIENT`: 테스트 이메일 수신자

## 🔧 설정 및 MockinG

### ConfigManager 테스트
- 싱글톤 패턴으로 인한 상태 공유 문제 해결
- `ConfigManager.reset_for_testing()` 메서드 사용
- 환경 변수 모킹으로 격리된 테스트 환경

### 메일 테스트
- `_get_email_config()` 함수 모킹
- 실제 API 호출 방지
- PostmarkClient 모킹

## 📊 테스트 품질 관리

### 코드 커버리지
```bash
# 커버리지 포함 테스트 실행
python -m pytest tests/ --cov=newsletter --cov-report=html

# 커버리지 리포트 확인
open htmlcov/index.html
```

### 테스트 성능
- 단위 테스트: < 10초
- 통합 테스트: < 30초
- 전체 테스트: < 2분

## 🚨 문제 해결

### 자주 발생하는 문제

1. **ConfigManager 상태 공유**
   ```python
   def setUp(self):
       ConfigManager.reset_for_testing()
   ```

2. **환경 변수 간섭**
   ```python
   @mock.patch.dict(os.environ, {"KEY": "value"}, clear=True)
   ```

3. **웹 서버 연결 오류**
   - 수동 테스트 전에 웹 서버 실행 필요
   - `python web/app.py` 또는 `uvicorn web.app:app`

4. **API 키 누락**
   - `.env` 파일 확인
   - 필수 API 키: `GEMINI_API_KEY`, `POSTMARK_SERVER_TOKEN`

### 로그 확인
```bash
# 자세한 로그와 함께 테스트 실행
python -m pytest tests/ -v -s --log-cli-level=DEBUG
```

## 📝 테스트 작성 가이드

### 새로운 테스트 추가 시

1. **적절한 디렉토리 선택**
   - 단위 테스트: `tests/unit_tests/`
   - 통합 테스트: `tests/integration/`
   - 수동 테스트: `tests/manual/`

2. **마커 사용**
   ```python
   @pytest.mark.mock_api
   def test_my_function():
       pass
   ```

3. **환경 설정**
   ```python
   def setUp(self):
       ConfigManager.reset_for_testing()
   ```

4. **모킹 패턴**
   ```python
   @mock.patch("module.function")
   def test_with_mock(mock_func):
       mock_func.return_value = "test_value"
   ```

이 구조를 통해 안정적이고 유지보수 가능한 테스트 환경을 제공합니다.
