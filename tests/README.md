# 뉴스레터 생성기 테스트 문서

이 문서는 Newsletter Generator 프로젝트의 테스트 구조와 실행 방법에 대해 설명합니다.

## 테스트 구조

프로젝트 테스트는 다음과 같은 구조로 구성되어 있습니다:

1. **메인 테스트** (루트 디렉토리)
   - 뉴스레터 생성, 필터링, 통합 기능에 대한 테스트
   - 주요 파일: `test_newsletter.py`, `test_article_filter.py`, `test_compose.py` 등

2. **API 테스트** (`api_tests/` 디렉토리)
   - API 키가 필요한, 외부 서비스 통합 테스트
   - 주요 파일: `test_serper_direct.py`, `test_collect.py`, `test_summarize.py` 등

3. **단위 테스트** (`unit_tests/` 디렉토리)
   - 독립적인 기능의 단위 테스트 (API 키 불필요)
   - 주요 파일: `test_date_utils.py`, `test_new_newsletter.py`, `test_weeks_ago.py` 등

4. **백업 테스트** (`_backup/` 디렉토리)
   - 이전 버전 또는 보관용 테스트 파일

## 뉴스레터 테스트 모드

뉴스레터 생성기는 두 가지 테스트 모드를 제공합니다:

1. **Template 모드**
   - 기존에 생성된 뉴스레터 데이터를 현재의 HTML 템플릿으로 재렌더링합니다.
   - 사용 방법: `newsletter test render_data_langgraph_*.json --mode template`
   - 주요 용도: 템플릿 디자인 변경 테스트

2. **Content 모드**
   - 이전에 수집된 기사 데이터로 처리, 요약, 편집 등의 전체 프로세스를 재실행합니다.
   - 사용 방법: `newsletter test collected_articles_*.json --mode content`
   - 주요 용도: 동일한 기사 데이터로 다양한 처리 알고리즘 테스트

### 테스트 모드 활용 사례

- **요약 알고리즘 개선**: 동일한 기사 데이터로 다양한 요약 프롬프트 비교
- **처리 알고리즘 테스트**: 필터링, 그룹화 등 처리 로직 변경 효과 테스트
- **템플릿 개선**: 디자인 변경 테스트
- **LLM 비교**: 다른 모델 간 요약 품질 비교

### 테스트 데이터 파일

- **render_data_langgraph_*.json**: 최종 렌더링 데이터 파일 (템플릿 모드용)
- **collected_articles_*.json**: 수집된 기사 데이터 파일 (콘텐츠 모드용)

이러한 파일들은 기본적으로 `output/intermediate_processing/` 디렉토리에 저장됩니다.

## 테스트 실행 방법

### 자동화된 테스트 실행

다음 명령어로 다양한 테스트를 실행할 수 있습니다:

```bash
# 모든 메인 테스트 실행 (백업 폴더 제외)
python run_tests.py --all

# API 테스트만 실행
python run_tests.py --api

# 단위 테스트만 실행
python run_tests.py --unit

# 사용 가능한 테스트 목록 확인
python run_tests.py --list

# 모든 테스트 목록 확인 (단위/API/백업 테스트 포함)
python run_tests.py --list-all

# 특정 테스트 파일 실행
python run_tests.py --test article_filter

# 코드 포맷팅 후 테스트 실행
python run_tests.py --format --all
```

### 수동 테스트 실행

특정 테스트 파일을 직접 실행하려면:

```bash
python -m pytest tests/test_article_filter.py -v
python -m pytest tests/unit_tests/test_date_utils.py -v
```

### 테스트 모드 실행

뉴스레터 생성 파이프라인의 일부를 테스트하려면:

```bash
# 템플릿 모드 테스트
newsletter test output/intermediate_processing/render_data_langgraph_20250522_143255.json --mode template

# 콘텐츠 모드 테스트
newsletter test output/collected_articles_AI_빅데이터.json --mode content

# 비용 추적 활성화
newsletter test output/collected_articles_AI_빅데이터.json --mode content --track-cost
```

## 테스트 작성 가이드라인

새로운 테스트를 작성할 때는 다음 가이드라인을 따르세요:

1. **테스트 유형 결정**:
   - API가 필요한 테스트는 `api_tests/` 디렉토리에 배치
   - 독립적인 단위 테스트는 `unit_tests/` 디렉토리에 배치
   - 통합 테스트는 루트 테스트 디렉토리에 배치

2. **테스트 명명 규칙**:
   - 파일 이름은 `test_[기능명].py` 형식을 따름
   - 테스트 함수 이름은 `test_[테스트_내용]` 형식을 따름

3. **테스트 독립성**:
   - 각 테스트는 독립적으로 실행할 수 있어야 함
   - 테스트 간 의존성 최소화
   - 필요한 경우 `pytest.fixture`를 사용하여 공통 설정

4. **모의 객체 사용**:
   - 외부 API를 사용하는 테스트는 가능한 모의 객체를 활용
   - 모의 객체는 `conftest.py` 또는 테스트 파일 내에 정의

## 주요 테스트 파일 목록

### 메인 테스트

| 파일 이름 | 설명 |
|-----------|------|
| `test_article_filter.py` | 기사 필터링 및 그룹화 기능 테스트 |
| `test_compose.py` | 뉴스레터 구성 및 렌더링 테스트 |
| `test_chains.py` | LangChain 체인 테스트 |
| `test_graph_date_parser.py` | 날짜 파싱 테스트 |
| `test_newsletter.py` | 뉴스레터 생성 통합 테스트 |
| `test_serper_api.py` | Serper.dev API 테스트 |
| `test_template.py` | 템플릿 렌더링 테스트 |
| `test_themes.py` | 주제 추출 테스트 |
| `test_tools.py` | 유틸리티 도구 테스트 |

### API 테스트

| 파일 이름 | 설명 |
|-----------|------|
| `api_tests/test_article_filter_integration.py` | 필터링 통합 테스트 |
| `api_tests/test_collect.py` | 기사 수집 테스트 |
| `api_tests/test_compose_integration.py` | 구성 통합 테스트 |
| `api_tests/test_gemini.py` | Gemini API 테스트 |
| `api_tests/test_serper_direct.py` | Serper API 직접 호출 테스트 |
| `api_tests/test_sources.py` | 뉴스 소스 테스트 |
| `api_tests/test_summarize.py` | 요약 기능 테스트 |

### 단위 테스트

| 파일 이름 | 설명 |
|-----------|------|
| `unit_tests/test_date_utils.py` | 날짜 유틸리티 테스트 |
| `unit_tests/test_new_newsletter.py` | 새 뉴스레터 테스트 |
| `unit_tests/test_weeks_ago.py` | 주 단위 계산 테스트 |
| `unit_tests/test_string_utils.py` | 문자열 유틸리티 테스트 |

## 테스트 데이터

테스트 데이터는 `tests/test_data/` 디렉토리에 저장되어 있습니다:

- `articles.json`: 테스트용 기사 데이터
- `keywords.json`: 테스트용 키워드 데이터
- `mock_responses/`: 모의 API 응답 데이터
- `templates/`: 테스트용 템플릿 파일

# Newsletter Generator 테스트 가이드

본 문서는 Newsletter Generator 프로젝트의 테스트 구조와 실행 방법을 설명합니다.

## 📊 테스트 구조

### 디렉토리 구조
```
tests/
├── 📁 api_tests/                    # API 테스트 (외부 서비스 호출)
│   ├── test_compact_newsletter_api.py   # Compact 뉴스레터 API 테스트
│   ├── test_theme_extraction.py         # 테마 추출 API 테스트
│   ├── test_search_improved.py          # 검색 API 테스트
│   └── ... (기타 API 테스트들)
├── 📁 unit_tests/                   # 단위 테스트
│   ├── test_template_manager.py         # 템플릿 관리 테스트
│   ├── test_date_utils.py               # 날짜 유틸리티 테스트
│   └── ... (기타 단위 테스트들)
├── 📄 test_compact_newsletter.py    # Compact 뉴스레터 단위 테스트
├── 📄 test_compact.py               # Compact 체인 테스트 (Legacy)
├── 📄 test_compose.py               # 컴포즈 기능 테스트
├── 📄 test_newsletter.py            # 뉴스레터 통합 테스트
└── 📄 TEST_REPORT_COMPACT_DEFINITIONS.md  # 테스트 보고서
```

## 🎯 테스트 분류

### Pytest 마커
- `@pytest.mark.unit`: 순수 단위 테스트 (API 호출 없음)
- `@pytest.mark.api`: API를 사용하는 테스트
- `@pytest.mark.integration`: 통합 테스트
- `@pytest.mark.slow`: 실행 시간이 긴 테스트

## 🚀 테스트 실행 방법

### 1단계: 단위 테스트 (빠른 검증, < 5초)
개발 중 빠른 피드백을 위한 테스트입니다.

```bash
# 모든 단위 테스트 실행
python -m pytest -m unit -v

# Compact 뉴스레터 단위 테스트만
python -m pytest tests/test_compact_newsletter.py -v

# 특정 단위 테스트 실행
python -m pytest tests/test_compact_newsletter.py::TestCompactNewsletterUnit::test_compact_definitions_generation -v

# 독립 실행
python tests/test_compact_newsletter.py
```

### 2단계: API 테스트 (완전한 검증, 1-15분)
외부 API를 사용하는 완전한 기능 테스트입니다.

```bash
# 모든 API 테스트 실행
python -m pytest -m api -v

# Compact 뉴스레터 API 테스트만
python -m pytest tests/api_tests/test_compact_newsletter_api.py -v

# 빠른 API 테스트만 (slow 제외)
python -m pytest -m "api and not slow" -v

# 독립 실행
python tests/api_tests/test_compact_newsletter_api.py
```

### 3단계: 전체 테스트 (최종 검증, 15-20분)
배포 전 완전한 검증을 위한 테스트입니다.

```bash
# 모든 테스트 실행
python -m pytest tests/ -v

# Compact 관련 모든 테스트
python -m pytest tests/test_compact*.py tests/api_tests/test_compact*.py -v

# 빠른 테스트만 (slow 제외)
python -m pytest -m "not slow" -v
```

## 📈 Compact 뉴스레터 테스트

### 단위 테스트 (`tests/test_compact_newsletter.py`)
외부 API 없이 순수한 기능 테스트:

| 테스트 | 설명 |
|--------|------|
| `test_compact_chain_creation` | 체인 생성 테스트 |
| `test_compact_definitions_generation` | 정의 추출 테스트 |
| `test_compact_template_rendering` | 템플릿 렌더링 테스트 |
| `test_definitions_extraction_edge_cases` | 엣지 케이스 테스트 |
| `test_template_data_validation` | 데이터 검증 테스트 |
| `test_error_handling_unit` | 에러 처리 테스트 |
| `test_definitions_content_validation` | 내용 검증 테스트 |

### API 테스트 (`tests/api_tests/test_compact_newsletter_api.py`)
실제 API를 사용하는 통합 테스트:

| 테스트 | 설명 | 마커 |
|--------|------|------|
| `test_compact_newsletter_generation_full_integration` | 완전 통합 테스트 | `api`, `integration` |
| `test_multiple_keywords_compact_api` | 여러 키워드 테스트 | `api`, `slow` |
| `test_compact_chain_with_real_llm` | 실제 LLM 테스트 | `api` |
| `test_fallback_definitions_with_mocked_llm` | 모킹 테스트 | `api`, `unit` |
| `test_compact_newsletter_with_different_topics` | 다양한 주제 테스트 | `api`, `slow` |
| `test_api_error_handling` | API 에러 처리 | `api` |

## 💡 개발 워크플로우 권장사항

### 개발 중
```bash
# 빠른 검증 (< 5초)
python -m pytest -m unit
```

### 기능 확인 시
```bash
# 중간 검증 (1-3분)
python -m pytest -m "api and not slow"
```

### PR 또는 배포 전
```bash
# 완전 검증 (15-20분)
python -m pytest tests/
```

## 🔧 설정

### pytest 설정 (setup.cfg)
```ini
[tool:pytest]
markers =
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    slow: marks tests as slow running tests
    api: marks tests that require API access
```

### 환경 변수
테스트 실행을 위해 다음 환경 변수가 필요할 수 있습니다:
- `GOOGLE_API_KEY`: Google AI API 키
- `SERPER_API_KEY`: Serper 검색 API 키

## 📝 테스트 작성 가이드

### 새로운 테스트 추가 시
1. **API 사용 여부 확인**: 외부 API를 사용하는가?
   - Yes → `tests/api_tests/` 디렉토리에 추가
   - No → `tests/` 디렉토리 또는 `tests/unit_tests/`에 추가

2. **적절한 마커 추가**:
   ```python
   @pytest.mark.unit      # 단위 테스트
   @pytest.mark.api       # API 테스트
   @pytest.mark.slow      # 긴 실행 시간
   @pytest.mark.integration  # 통합 테스트
   ```

3. **독립 실행 가능하게 작성**:
   ```python
   if __name__ == "__main__":
       # 독립 실행 코드
   ```

## 📊 커버리지

현재 테스트 커버리지는 `setup.cfg`에서 설정되어 있으며, 최소 10% 이상을 유지하도록 설정되어 있습니다.

```bash
# 커버리지 포함 테스트 실행
python -m pytest --cov=newsletter tests/
```

---

**더 자세한 정보는 `TEST_REPORT_COMPACT_DEFINITIONS.md`를 참조하세요.**
