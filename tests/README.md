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
