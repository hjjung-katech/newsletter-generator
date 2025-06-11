# Newsletter Generator 테스트 실행 가이드

## 🎯 현재 발생한 문제와 해결 방안

### ❌ 문제점
- `python run_tests.py dev` 실행 시 E2E 테스트가 포함되어 웹 서버 연결 오류 발생
- 7개 E2E 테스트가 실패하여 전체 테스트 결과가 왜곡됨
- 테스트 분류가 불명확하여 의존성 문제 발생

### ✅ 해결책
- E2E 테스트를 `tests/e2e/` 디렉토리로 분리
- 배포 테스트를 `tests/deployment/` 디렉토리로 분리
- 테스트 마커 시스템 개선으로 실행 환경 구분

## 🚀 올바른 테스트 실행 방법

### 1. 일반 개발 시 (권장)
```bash
# 단위 테스트 + Mock API 테스트 (가장 빠름)
python run_tests.py dev

# 또는 필수 테스트만
python tests/run_essential_tests.py
```

### 2. 기능 개발 완료 후
```bash
# 통합 테스트 포함 (실제 API 키 필요)
RUN_INTEGRATION_TESTS=1 python run_tests.py integration
```

### 3. E2E 테스트 실행 (웹 서버 필요)
```bash
# Terminal 1: 웹 서버 시작
cd web
python app.py

# Terminal 2: E2E 테스트 실행
python -m pytest tests/e2e/ -v
```

### 4. 배포 후 검증
```bash
# Railway 배포 검증
python tests/deployment/smoke_test.py --railway

# 특정 URL 검증
python tests/deployment/smoke_test.py --url https://your-app.railway.app
```

## 📂 개선된 테스트 구조

```
tests/
├── unit_tests/           # ⚡ 단위 테스트 (외부 의존성 없음)
├── integration/         # 🔗 통합 테스트 (Mock API)
├── e2e/                # 🌐 E2E 테스트 (웹 서버 필요)
│   └── test_railway_e2e.py
├── deployment/         # 🚀 배포 검증 테스트
│   ├── smoke_test.py
│   └── test_railway.py
├── manual/             # 👤 수동 테스트
└── api_tests/          # 🌍 외부 API 테스트
```

## ⚙️ 환경 변수 설정

### 기본 테스트용
```bash
# 개발 환경 (권장)
export RUN_REAL_API_TESTS=0
export RUN_MOCK_API_TESTS=1
export RUN_INTEGRATION_TESTS=0
```

### E2E 테스트용
```bash
export TEST_BASE_URL=http://localhost:5000
export TEST_EMAIL=test@example.com
```

### 배포 테스트용
```bash
export RAILWAY_PRODUCTION_URL=https://your-app.railway.app
export DEPLOYED_URL=https://your-app.railway.app
```

### 실제 API 테스트용 (필요시에만)
```bash
export GEMINI_API_KEY=your_gemini_key
export SERPER_API_KEY=your_serper_key
export POSTMARK_SERVER_TOKEN=your_postmark_token
```

## 🏷️ 테스트 마커별 실행

```bash
# 단위 테스트만
python -m pytest -m unit

# Mock API 테스트만
python -m pytest -m mock_api

# E2E 테스트만 (웹 서버 필요)
python -m pytest -m e2e

# 배포 테스트만
python -m pytest -m deployment

# 실제 API 테스트만 (API 키 필요)
python -m pytest -m real_api

# 한국어 인코딩 테스트만
python -m pytest -m korean

# 느린 테스트 제외하고 실행
python -m pytest -m "not slow"
```

## 🇰🇷 한국어 테스트 실행

한국어 키워드를 사용한 CLI 테스트:

```bash
# 한국어 테스트만 실행
python -m pytest tests/integration/test_korean_cli.py -v

# 한국어 테스트 마커로 실행
python -m pytest -m korean -v

# 한국어 테스트 직접 실행 (단일 테스트)
python tests/integration/test_korean_cli.py

# 통합 테스트 중 한국어만
python -m pytest -m "korean and integration" -v
```

### 한국어 테스트 특징
- **인코딩 처리**: UTF-8, CP949, EUC-KR 등 안전한 디코딩
- **키워드 검증**: 한국어 키워드가 결과에 포함되는지 확인
- **혼합 언어**: 한국어와 영어 키워드 혼합 테스트
- **특수 문자**: 이모지, 한자 등 특수 문자 인코딩 테스트

## 🔧 문제 해결

### E2E 테스트 연결 오류
```
httpx.ConnectError: [WinError 10061] 대상 컴퓨터에서 연결을 거부
```
**해결**: 웹 서버 실행 → `cd web && python app.py`

### API 키 관련 오류
```
External API dependency failed: API key error
```
**해결**: `.env` 파일에 API 키 설정 또는 Mock 테스트로 전환

### 테스트 실행 시간 최적화
- 개발 중: `python run_tests.py dev` (< 30초)
- 기능 검증: `python tests/run_essential_tests.py` (< 20초)
- 전체 검증: `RUN_INTEGRATION_TESTS=1 python run_tests.py integration` (< 2분)

## 📊 테스트 성능 목표

| 테스트 유형 | 목표 시간 | 실행 조건 |
|------------|-----------|-----------|
| 단위 테스트 | < 10초 | 항상 실행 |
| Mock API 테스트 | < 20초 | 개발 시 |
| 통합 테스트 | < 30초 | PR 시 |
| E2E 테스트 | < 2분 | 수동 실행 |
| 배포 테스트 | < 1분 | 배포 후 |

## 🚨 주의사항

1. **E2E 테스트는 웹 서버 실행 필수**
   - `run_tests.py dev`에서 자동 제외됨
   - 수동으로 웹 서버 시작 후 실행

2. **실제 API 테스트는 할당량 소모**
   - 개발 중에는 Mock API 사용 권장
   - 통합 테스트 시에만 실제 API 사용

3. **배포 테스트는 실제 서비스 대상**
   - 로컬 개발 환경과 분리
   - Railway 배포 후에만 실행

이 가이드를 따르면 안정적이고 효율적인 테스트 환경을 구축할 수 있습니다. 