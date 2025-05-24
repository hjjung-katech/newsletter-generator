# 뉴스레터 생성기 테스트 문서

이 문서는 Newsletter Generator 프로젝트의 테스트 구조와 실행 방법에 대해 설명합니다.

## 🎯 환경별 테스트 전략

Newsletter Generator는 **환경별 테스트 전략**을 도입하여 개발 효율성과 품질을 동시에 확보합니다:

| 환경 | 목적 | 실행 대상 | API 할당량 | 실행 시간 |
|------|------|-----------|------------|-----------|
| **dev** | 개발용 빠른 피드백 | Mock API + 핵심 단위 테스트 | 소모 없음 | ~20초 |
| **ci** | CI/CD용 전체 검증 | 전체 검증 (Real API 제외) | 소모 없음 | ~35초 |
| **unit** | 순수 단위 테스트 | API 의존성 완전 배제 | 소모 없음 | ~21초 |
| **integration** | 실제 환경 검증 | 모든 테스트 (Real API 포함) | 할당량 소모 | 상황에 따라 다름 |

### 🚀 통합 테스트 스크립트

**새로운 통합 테스트 관리 도구** (`run_tests.py`):

```bash
# 환경별 실행
python run_tests.py dev              # 개발용 빠른 테스트
python run_tests.py ci               # CI/CD용 전체 검증  
python run_tests.py unit             # 순수 단위 테스트
python run_tests.py integration      # 실제 API 포함 검증

# 디렉토리별 실행
python run_tests.py --api            # API 테스트만
python run_tests.py --unit-tests     # 단위 테스트만

# 유틸리티
python run_tests.py --format         # 코드 포맷팅
python run_tests.py --list           # 테스트 목록 조회
```

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
├── 📄 test_unified_architecture.py  # 🆕 통합 아키텍처 테스트
├── 📄 test_newsletter_mocked.py     # 🆕 Mock 기반 뉴스레터 테스트
├── 📄 test_compose.py               # 컴포즈 기능 테스트
└── 📄 conftest.py                   # 🆕 환경별 테스트 설정
```

### 🎯 테스트 분류 (Pytest 마커)

```python
@pytest.mark.unit         # 순수 단위 테스트 (API 호출 없음)
@pytest.mark.api          # API를 사용하는 테스트  
@pytest.mark.mock_api     # Mock API 테스트
@pytest.mark.real_api     # 실제 API 테스트
@pytest.mark.integration  # 통합 테스트
@pytest.mark.slow         # 실행 시간이 긴 테스트
@pytest.mark.requires_quota # API 할당량이 필요한 테스트
```

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
   - 사용 방법: `newsletter test render_data_langgraph*.json --mode template`
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

## 🚀 테스트 실행 방법

### 환경별 실행 (권장)

```bash
# 개발 중 빠른 검증 (~20초)
python run_tests.py dev

# 기능 확인 시 중간 검증 (~35초)  
python run_tests.py ci

# 순수 단위 테스트만 (~21초)
python run_tests.py unit

# 배포 전 완전한 검증 (API 할당량 소모)
python run_tests.py integration
```

### 디렉토리별 실행

```bash
# API 테스트만 실행
python run_tests.py --api

# 단위 테스트만 실행
python run_tests.py --unit-tests

# 특정 테스트 파일 실행
python run_tests.py --test test_unified_architecture

# 사용 가능한 테스트 목록 확인
python run_tests.py --list
```

### 수동 테스트 실행

특정 테스트 파일을 직접 실행하려면:

```bash
# Pytest로 실행
python -m pytest tests/test_unified_architecture.py -v
python -m pytest tests/unit_tests/test_date_utils.py -v

# 직접 실행 (독립 실행 지원 파일만)
python tests/test_unified_architecture.py
python tests/test_compact_newsletter.py
```

### 뉴스레터 CLI 테스트 모드

```bash
# 템플릿 모드 테스트
newsletter test output/intermediate_processing/render_data_langgraph_20250522_143255.json --mode template

# 콘텐츠 모드 테스트
newsletter test output/collected_articles_AI_빅데이터.json --mode content

# 비용 추적 활성화
newsletter test output/collected_articles_AI_빅데이터.json --mode content --track-cost
```

## 📝 주요 테스트 파일 목록

### 🔧 핵심 테스트

| 파일 이름 | 설명 | 마커 |
|-----------|------|------|
| `test_unified_architecture.py` | **🆕** 통합 아키텍처 및 10단계 플로우 검증 | `unit` |
| `test_newsletter_mocked.py` | **🆕** Mock 기반 뉴스레터 생성 테스트 | `mock_api` |
| `test_compact_newsletter.py` | Compact 뉴스레터 단위 테스트 | `unit` |
| `test_compose.py` | 뉴스레터 구성 및 렌더링 테스트 | `unit` |

### 📡 API 테스트

| 파일 이름 | 설명 | 마커 |
|-----------|------|------|
| `api_tests/test_compact_newsletter_api.py` | Compact 뉴스레터 API 통합 테스트 | `api`, `integration` |
| `api_tests/test_serper_direct.py` | Serper API 직접 호출 테스트 | `api` |
| `api_tests/test_collect.py` | 기사 수집 API 테스트 | `api` |
| `api_tests/test_summarize.py` | 요약 기능 API 테스트 | `api` |

### 🧩 단위 테스트

| 파일 이름 | 설명 | 마커 |
|-----------|------|------|
| `unit_tests/test_date_utils.py` | 날짜 유틸리티 테스트 | `unit` |
| `unit_tests/test_new_newsletter.py` | 새 뉴스레터 기능 테스트 | `unit` |
| `unit_tests/test_weeks_ago.py` | 주 단위 계산 테스트 | `unit` |
| `unit_tests/test_string_utils.py` | 문자열 유틸리티 테스트 | `unit` |

## 🔧 테스트 작성 가이드라인

### 새로운 테스트 추가 시

1. **테스트 유형 결정**:
   - **아키텍처/통합 검증** → `tests/` 루트 디렉토리
   - **API 의존성 있음** → `tests/api_tests/` 디렉토리
   - **순수 단위 테스트** → `tests/unit_tests/` 디렉토리

2. **적절한 마커 추가**:
   ```python
   @pytest.mark.unit         # 순수 단위 테스트
   @pytest.mark.mock_api     # Mock API 테스트
   @pytest.mark.real_api     # 실제 API 테스트
   @pytest.mark.integration  # 통합 테스트
   @pytest.mark.slow         # 긴 실행 시간
   @pytest.mark.requires_quota # API 할당량 필요
   ```

3. **독립 실행 지원**:
   ```python
   if __name__ == "__main__":
       # 독립 실행을 위한 main() 함수 호출
       main()
   ```

4. **환경별 조건부 실행**:
   ```python
   # conftest.py의 환경 변수 기반 스킵 사용
   # RUN_REAL_API_TESTS, RUN_MOCK_API_TESTS 등
   ```

### 테스트 명명 규칙

- **파일 이름**: `test_[기능명].py`
- **클래스 이름**: `Test[기능명]`  
- **함수 이름**: `test_[테스트_내용]`

## 📊 테스트 데이터

테스트 데이터는 `tests/test_data/` 디렉토리에 저장되어 있습니다:

- `articles.json`: 테스트용 기사 데이터
- `keywords.json`: 테스트용 키워드 데이터
- `mock_responses/`: 모의 API 응답 데이터
- `templates/`: 테스트용 템플릿 파일

## 💡 개발 워크플로우 권장사항

### 개발 중
```bash
# 빠른 검증 (~20초)
python run_tests.py dev
```

### 기능 확인 시
```bash
# 중간 검증 (~35초)
python run_tests.py ci
```

### PR 또는 배포 전
```bash
# 완전 검증 (API 할당량 소모)
python run_tests.py integration
```

## 🔧 환경 설정

### 환경 변수
테스트 실행을 위해 다음 환경 변수를 설정할 수 있습니다:

```bash
# API 테스트 제어
export RUN_REAL_API_TESTS=true    # 실제 API 테스트 실행
export RUN_MOCK_API_TESTS=true    # Mock API 테스트 실행

# API 키 (실제 API 테스트용)
export GOOGLE_API_KEY=your_key    # Google AI API 키
export SERPER_API_KEY=your_key    # Serper 검색 API 키
```

### Pytest 설정 (setup.cfg)
```ini
[tool:pytest]
markers =
    unit: 순수 단위 테스트 (API 호출 없음)
    api: API를 사용하는 테스트
    mock_api: Mock API 테스트
    real_api: 실제 API 테스트
    integration: 통합 테스트
    slow: 실행 시간이 긴 테스트
    requires_quota: API 할당량이 필요한 테스트
```

## 📈 커버리지

현재 테스트 커버리지는 `setup.cfg`에서 설정되어 있으며, 최소 10% 이상을 유지하도록 설정되어 있습니다.

```bash
# 커버리지 포함 테스트 실행
python run_tests.py ci --coverage
```

---

**🎯 환경별 테스트 전략으로 개발 효율성과 품질을 동시에 확보하세요!**
