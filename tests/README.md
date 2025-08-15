# Newsletter Generator 테스트 가이드

## 🧪 테스트 철학

이 프로젝트의 테스트는 **신뢰성**과 **속도**를 핵심 가치로 삼습니다. CI/CD 파이프라인에서는 빠르고 안정적인 단위 테스트와 모킹(Mocking) 기반의 통합 테스트를 실행하여 변경사항을 신속하게 검증합니다. 실제 API를 호출하거나 웹 서버에 의존하는 E2E 테스트는 개발자가 로컬 환경이나 스테이징 환경에서 수동으로 실행하여 실제 사용 시나리오를 검증합니다.

## 📂 테스트 구조

테스트는 목적에 따라 명확하게 분류되어 관리됩니다.

```
tests/
├── test_data/              # 🧪 테스트 실행에 사용되는 데이터 파일
├── test_api.py             # 🌐 웹 API 동작 검증 (웹 서버 의존)
├── test_article_filter.py  # 🧹 기사 필터링 및 정제 로직 검증
├── test_chains.py          # ⛓️ LangChain 및 LangGraph 체인 검증
├── test_ci.py              # 🤖 CI 환경 특별 케이스 검증
├── test_compose.py         # 📝 뉴스레터 콘텐츠 생성 및 템플릿 렌더링 통합 검증
├── test_delivery.py        # 📧 이메일 및 로컬 파일 전송 기능 통합 검증
├── test_minimal.py         # 📦 최소 설치 환경 동작 검증
├── test_news_integration.py # 🔗 기사 수집부터 처리까지의 통합 흐름 검증
├── test_scoring.py         # 💯 기사 점수 계산 로직 검증
├── test_security.py        # 🛡️ 보안 관련 기능 검증
├── test_suggest.py         # ✨ 키워드 추천 기능 검증
├── test_tools.py           # 🛠️ 외부 API 연동 도구(검색, 키워드 생성 등) 검증
└── README.md               # 📖 이 파일
```

### 주요 테스트 파일 설명

- **`test_compose.py`**: 상세(Detailed) 및 요약(Compact) 뉴스레터의 HTML 생성, 템플릿 데이터 처리, 테마 생성 등 전반적인 콘텐츠 구성(Composition) 과정을 통합적으로 테스트합니다.
- **`test_delivery.py`**: Postmark API를 이용한 이메일 발송 및 로컬 파일 저장 기능을 통합적으로 테스트합니다.
- **`test_news_integration.py`**: 사용자의 키워드 입력부터 기사 수집, 필터링, 점수 계산까지 이어지는 핵심 데이터 파이프라인을 검증하는 가장 중요한 통합 테스트 중 하나입니다.
- **`test_tools.py`**: `Serper`, `Gemini` 등 외부 API를 호출하는 각 도구의 요청/응답 형식을 모킹하여 테스트합니다.

## 🚀 테스트 실행 방법

### 1. 빠른 단위/통합 테스트 (개발 중 권장)

외부 API 호출 없이, 모킹된 데이터를 사용하여 빠르게 실행됩니다. CI 환경에서 기본으로 실행되는 테스트입니다.

```bash
pytest
```

### 2. 특정 기능 테스트

특정 파일이나 디렉토리를 지정하여 테스트를 실행할 수 있습니다.

```bash
# 컴포지션 관련 기능만 테스트
pytest tests/test_compose.py

# 이메일 발송 기능만 테스트
pytest tests/test_delivery.py
```

### 3. 실제 API를 이용한 통합 테스트 (수동 실행)

**주의: 이 테스트는 실제 API 크레딧을 사용합니다.**

로컬 환경에서 `.env` 파일에 실제 API 키를 설정한 후, 아래 명령어로 실행할 수 있습니다.

```bash
# POSTMARK_SERVER_TOKEN, TEST_EMAIL_RECIPIENT 환경변수 설정 필요
pytest --run-integration
```

## 🏷️ Pytest 마커

테스트 실행 범위를 효과적으로 제어하기 위해 마커를 사용합니다.

- `@pytest.mark.unit`: 외부 의존성이 없는 순수한 단위 테스트입니다.
- `@pytest.mark.mock_api`: `requests`나 외부 라이브러리를 모킹하여 API 상호작용을 시뮬레이션하는 테스트입니다.
- `@pytest.mark.integration`: 실제 API 키가 있을 경우, 외부 서비스와 실제로 통신하여 통합 동작을 검증하는 테스트입니다. (CI에서는 기본적으로 비활성화)

```bash
# 단위 테스트만 실행
pytest -m unit

# 모킹된 API 테스트만 실행
pytest -m mock_api

# 통합 테스트만 실행 (API 키 필요)
pytest -m integration
```

## 🔧 테스트 환경 설정

### 의존성 설치

테스트 실행에 필요한 모든 의존성은 `requirements.txt`와 `requirements-dev.txt`에 정의되어 있습니다.

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 환경 변수

실제 API를 사용하는 통합 테스트를 실행하려면, 프로젝트 루트에 `.env` 파일을 생성하고 아래와 같이 필요한 키를 설정해야 합니다.

```dotenv
# .env.example 파일을 복사하여 사용하세요.

# 이메일 통합 테스트용
POSTMARK_SERVER_TOKEN="your_postmark_token"
EMAIL_SENDER="sender@example.com"
TEST_EMAIL_RECIPIENT="recipient@example.com"

# 뉴스 검색 및 LLM 기능 테스트용
SERPER_API_KEY="your_serper_key"
GEMINI_API_KEY="your_gemini_key"
```