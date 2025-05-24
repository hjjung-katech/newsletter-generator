# Newsletter Generator

[![CI](https://github.com/your-org/newsletter-generator/workflows/CI/badge.svg)](https://github.com/your-org/newsletter-generator/actions/workflows/ci.yml)
[![Code Quality](https://github.com/your-org/newsletter-generator/workflows/Code%20Quality/badge.svg)](https://github.com/your-org/newsletter-generator/actions/workflows/code-quality.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 최근 업데이트: 통합 뉴스레터 생성 아키텍처

뉴스레터 생성 시스템이 **공용 함수 기반의 통합 아키텍처**로 재구성되었습니다. 이제 Compact와 Detailed 버전이 동일한 핵심 로직을 공유하면서도 각각의 특성에 맞는 결과물을 생성합니다.

### 🏗️ 통합 아키텍처 개요

**핵심 개념**: 하나의 `compose_newsletter()` 함수가 설정 기반으로 두 가지 스타일을 모두 처리

```python
# 통합 함수 사용 예시
from newsletter.compose import compose_newsletter

# Compact 버전 생성
compact_html = compose_newsletter(data, template_dir, "compact")

# Detailed 버전 생성  
detailed_html = compose_newsletter(data, template_dir, "detailed")
```

### 📋 10단계 통합 플로우

두 버전 모두 동일한 10단계 플로우를 따르며, 각 단계에서 설정에 따라 다른 동작을 수행합니다:

| 단계 | 설명 | Compact 버전 | Detailed 버전 |
|------|------|--------------|---------------|
| 1 | **뉴스키워드 결정** | 도메인 기반 또는 직접 키워드 | 동일 |
| 2 | **뉴스 기사 검색** | 다양한 소스에서 기사 수집 | 동일 |
| 3 | **뉴스기사 기간 필터링** | 최신 기사만 선별 | 동일 |
| 4 | **뉴스 기사 점수 채점** | 중요도 기반 순위 매기기 | 동일 |
| 5 | **상위 3개 기사 선별** | 가장 중요한 3개 기사 추출 | 동일 |
| 6 | **주제 그룹핑** | **최대 3개 그룹** | **최대 6개 그룹** |
| 7 | **내용 요약** | **간단한 요약** | **상세한 한문단 요약** |
| 8 | **용어 정의** | **최대 3개** | **그룹별 0-2개, 중복 없음** |
| 9 | **생각해볼거리 생성** | 간결한 메시지 | 상세한 인사이트 |
| 10 | **템플릿 기반 최종 생성** | `newsletter_template_compact.html` | `newsletter_template.html` |

### ⚙️ 설정 기반 차이점 관리

`NewsletterConfig` 클래스가 두 버전의 차이점을 중앙에서 관리합니다:

```python
# Compact 설정
{
    "max_articles": 10,           # 총 기사 수 제한
    "top_articles_count": 3,      # 상위 기사 수
    "max_groups": 3,              # 최대 그룹 수
    "max_definitions": 3,         # 최대 용어 정의 수
    "summary_style": "brief",     # 요약 스타일
    "template_name": "newsletter_template_compact.html"
}

# Detailed 설정  
{
    "max_articles": None,         # 모든 필터된 기사
    "top_articles_count": 3,      # 상위 기사 수
    "max_groups": 6,              # 최대 그룹 수
    "max_definitions": None,      # 그룹별 제한 없음
    "summary_style": "detailed",  # 요약 스타일
    "template_name": "newsletter_template.html"
}
```

### 🎯 템플릿 스타일 선택

CLI에서 간단하게 스타일을 선택할 수 있습니다:

```bash
# Compact 버전 (간결한 형태)
newsletter run --keywords "AI 반도체" --template-style compact

# Detailed 버전 (상세한 형태) - 기본값
newsletter run --keywords "AI 반도체" --template-style detailed
```

### 🚀 아키텍처 장점

- **코드 재사용성**: 동일한 핵심 로직을 공유하여 중복 코드 제거
- **일관성**: 두 버전 간 동작 및 품질 일관성 보장  
- **확장성**: 새로운 템플릿 스타일을 쉽게 추가 가능
- **유지보수성**: 단일 코드베이스로 관리하여 버그 수정 및 기능 개선 용이
- **테스트 용이성**: 통합된 함수로 테스트 작성 및 검증 간소화

### 🔧 하위 호환성

기존 코드와의 호환성을 위해 레거시 함수들이 유지됩니다:

```python
# 기존 함수들 (내부적으로 통합 함수 호출)
compose_newsletter_html()        # -> compose_newsletter(data, template_dir, "detailed")
compose_compact_newsletter_html() # -> compose_newsletter(data, template_dir, "compact")
```

---

## 최근 업데이트: 테스트 모드 기능 추가

newsletter test 명령어가 추가되어 다음과 같은 기능을 제공합니다:

- **Template 모드**: 기존 뉴스레터 데이터를 현재 HTML 템플릿으로 재렌더링
- **Content 모드**: 이전에 수집된 기사 데이터를 사용하여 처리, 요약, 편집 등의 전체 후속 프로세스 재실행

이를 통해 동일한 뉴스 수집 데이터로 여러 가지 뉴스레터 생성 테스트가 가능해졌습니다.

## 최근 업데이트: 필터링 기능 추가

최근 시스템에 다음과 같은 필터링 기능이 추가되었습니다:

- **중복 기사 감지 및 제거**: URL 및 제목 기반으로 중복 기사 필터링
- **주요 뉴스 소스 우선순위**: 티어 시스템을 적용하여 신뢰할 수 있는 소스 우선 표시
- **도메인 다양성 보장**: 특정 출처에 편중되지 않도록 도메인별 기사 수 제한
- **키워드별 기사 그룹화**: 다양한 매칭 알고리즘을 적용한 효과적인 그룹화
- **유사 기사 제거**: 제목 유사도 기반으로 거의 동일한 기사를 추가로 필터링
- **핵심 뉴스 3선**: 중요도를 계산해 가장 중요한 3개 기사를 상단에 노출

이러한 개선 사항은 뉴스레터의 품질과 관련성을 크게 향상시켰습니다.

## 개요

Newsletter Generator는 내부 연구원이 입력(또는 자동 추천)한 키워드를 기반으로 **다양한 뉴스 소스**에서 최신 뉴스를 수집‧요약하여 이메일로 발송하고, 필요 시 Google Drive에 저장하는 Python CLI 도구입니다.

자세한 프로젝트 요구사항은 [PRD.md](PRD.md) 문서를 참고하세요.

---

## 설치 및 사용법

### 설치 방법

```bash
# 개발 환경 설정
git clone https://github.com/username/newsletter-generator.git
cd newsletter-generator
pip install -e .

# 또는 배포된 패키지 설치
pip install newsletter-generator

# 추가로 feedparser 설치
pip install feedparser==6.0.11
```

### 환경 설정

`.env` 파일을 프로젝트 루트 디렉터리에 생성하고 다음과 같이 API 키를 설정하세요:

```
# 뉴스 수집용 API 키
NEWS_API_KEY=your_news_api_key
SERPER_API_KEY=your_serper_api_key

# 네이버 뉴스 API (선택사항)
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret

# 추가 RSS 피드 URL (쉼표로 구분, 선택사항)
ADDITIONAL_RSS_FEEDS=https://example.com/rss/feed1.xml,https://example.com/rss/feed2.xml

# 생성형 AI 요약용 API 키
GEMINI_API_KEY=your_gemini_api_key

# 이메일 발송용 API 키 (선택사항)
SENDGRID_API_KEY=your_sendgrid_api_key
EMAIL_SENDER=sender@example.com

# Google Drive 업로드용 (선택사항)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# LangSmith 연동 (선택사항)
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_TRACING_V2=1
LANGCHAIN_PROJECT=your_project_name
```

### 사용 방법

뉴스레터를 생성하는 방법은 여러 가지가 있습니다.

**1. `suggest` 명령어로 키워드를 추천받고, 추천된 명령어로 뉴스레터 생성 (2단계)**

```bash
# 특정 분야의 트렌드 키워드 추천받기
newsletter suggest --domain "자율주행"

# 위 명령 실행 후, 터미널에 다음과 같이 실행할 명령어가 안내됩니다.
# To generate a newsletter with these keywords, you can use the following command:
# newsletter run --keywords "추천된 키워드1,추천된 키워드2,..."

# 안내된 명령어를 복사하여 실행
newsletter run --keywords "추천된 키워드1,추천된 키워드2,..." --output-format html 
```

**2. `run` 명령어에 `--domain` 옵션을 사용하여 키워드 생성부터 뉴스레터 발행까지 한 번에 실행 (1단계)**

```bash
# 특정 분야의 키워드를 자동으로 생성하여 뉴스레터 만들기
newsletter run --domain "친환경 자동차" --output-format html

# 생성할 키워드 개수 지정 (기본값: 10개)
newsletter run --domain "배터리 기술" --suggest-count 5 --output-format md

# 특정 이메일 주소로 발송
newsletter run --domain "AI" --to recipient@example.com

# Google Drive에도 저장
newsletter run --domain "머신러닝" --drive

# 모든 옵션 함께 사용
newsletter run --domain "반도체" --suggest-count 7 --to recipient@example.com --output-format html --drive

# 비용 추적 기능 활성화 (LangSmith 통합)
newsletter run --domain "인공지능" --track-cost --output-format html
```

**3. 직접 키워드 지정 및 필터링 옵션 활용**

```bash
# 키워드로 뉴스 검색 및 뉴스레터 생성
newsletter run --keywords "자율주행,ADAS" --output-format html

# 필터링 옵션 적용 (중복 제거, 키워드별 그룹화, 주요 소스 우선 처리)
newsletter run --keywords "AI반도체,HBM" --max-per-source 3 --output-format html 

# 특정 필터링 기능 비활성화
newsletter run --keywords "메타버스,XR" --no-filter-duplicates --no-major-sources-filter --output-format html

# 템플릿 스타일 선택
newsletter run --keywords "AI,머신러닝" --template-style compact --output-format html
newsletter run --keywords "AI,머신러닝" --template-style detailed --output-format html
```

**4. `test` 명령어로 기존 데이터를 활용한 테스트 수행**

```bash
# Template 모드: 기존 뉴스레터 데이터를 현재 HTML 템플릿으로 재렌더링
newsletter test output\render_data_langgraph_20250522_143255.json --mode template

# Content 모드: 이전에 수집된 기사 데이터로 전체 프로세스 재실행 (수집 단계 제외)
newsletter test output\collected_articles_AI_빅데이터.json --mode content

# 비용 추적 활성화
newsletter test output\collected_articles_AI_빅데이터.json --mode content --track-cost

# 커스텀 출력 파일 지정
newsletter test output\collected_articles_AI_빅데이터.json --mode content --output custom_output.html
```

### 주요 명령어 옵션

**`newsletter run` 명령어 옵션:**

| 옵션                        | 설명                                                                  | 기본값 (옵션 미지정 시 동작)                    |
| --------------------------- | --------------------------------------------------------------------- | ----------------------------------------------- |
| **기본 옵션**               |                                                                       |                                                 |
| `--keywords`                | 검색할 키워드 (쉼표로 구분)                                           | 없음 (필수 또는 `--domain` 사용)                |
| `--domain`                  | 키워드를 생성할 분야                                                  | 없음 (필수 또는 `--keywords` 사용)              |
| `--suggest-count`           | `--domain` 사용 시 생성할 키워드 개수                                 | 10                                              |
| `--period`, `-p`            | 최신 뉴스 수집 기간(일 단위)                                          | 14                                              |
| **출력 옵션**               |                                                                       |                                                 |
| `--to`                      | 뉴스레터를 발송할 이메일 주소                                         | 없음 (이메일 발송 건너뜀)                       |
| `--output-format`           | 로컬에 저장할 형식 (`html` 또는 `md`). `--drive` 사용 시에도 이 형식을 따름. | `html` (또는 `--drive`만 지정 시 Drive에만 저장)  |
| `--drive`                   | Google Drive에 뉴스레터 저장 여부                                     | 저장 안 함                                      |
| `--track-cost`              | LangSmith 비용 추적 활성화 여부 | 비활성화 |
| **필터링 옵션**             |                                                                       |                                                 |
| `--max-per-source INT`      | 도메인별 최대 기사 수를 지정합니다.                                     | 모든 기사 포함                                  |
| `--no-filter-duplicates`    | 지정 시, 중복 기사 필터링을 비활성화합니다.                             | 중복 기사 필터링 수행                           |
| `--no-major-sources-filter` | 지정 시, 주요 뉴스 소스 우선순위 지정을 비활성화합니다.                 | 주요 뉴스 소스 우선순위 지정 수행               |
| `--no-group-by-keywords`    | 지정 시, 키워드별 기사 그룹화를 비활성화합니다.                         | 키워드별 기사 그룹화 수행                       |

**`newsletter suggest` 명령어 옵션:**

| 옵션       | 설명                             | 기본값 |
| ---------- | -------------------------------- | ------ |
| `--domain` | 추천 키워드를 생성할 분야 (필수) | -      |
| `--count`  | 생성할 키워드 개수               | 10     |

**`newsletter test` 명령어 옵션:**

| 옵션            | 설명                                     | 기본값                |
| --------------- | ---------------------------------------- | --------------------- |
| `data_file`     | 테스트에 사용할 데이터 파일 경로 (필수)  | -                     |
| `--output`      | 생성된 뉴스레터의 출력 파일 경로         | 자동 생성 (output/ 디렉토리) |
| `--mode`        | 실행 모드 (`template` 또는 `content`)    | `template`            |
| `--track-cost`  | LangSmith 비용 추적 활성화 여부          | 비활성화              |

**테스트 모드 설명:**

1. **Template 모드**: 기존에 생성된 뉴스레터 데이터(render_data*.json)를 사용하여 현재 HTML 템플릿으로 재렌더링합니다. 템플릿 변경 테스트에 유용합니다.

2. **Content 모드**: 동일한 기사 데이터로 다양한 처리/요약 방식을 테스트할 수 있습니다. 기사 수집 단계를 건너뛰고 처리/요약 프로세스만 실행합니다.

---

## 다양한 뉴스 소스

Newsletter Generator는 다양한 뉴스 소스를 통합하여 광범위한 뉴스 기사를 수집합니다:

### 지원되는 뉴스 소스

1. **Serper.dev API (Google 검색)**
   - 키워드 기반으로 Google 검색을 통해 뉴스 기사를 수집합니다.
   - 설정: `.env` 파일에 `SERPER_API_KEY` 값 필요

2. **RSS 피드**
   - 국내 주요 언론사 RSS 피드를 통해 최신 뉴스를 수집합니다.
   - 기본 제공 피드:
     - 연합뉴스TV: [https://www.yonhapnewstv.co.kr/feed/](https://www.yonhapnewstv.co.kr/feed/)
     - 한겨레: [https://www.hani.co.kr/rss/](https://www.hani.co.kr/rss/)
     - 동아일보: [https://rss.donga.com/total.xml](https://rss.donga.com/total.xml)
     - 경향신문: [https://www.khan.co.kr/rss/rssdata/total_news.xml](https://www.khan.co.kr/rss/rssdata/total_news.xml)
   - 추가 피드 설정: `.env` 파일에 `ADDITIONAL_RSS_FEEDS` 값을 쉼표로 구분된 URL 목록으로 설정

3. **네이버 뉴스 API**
   - 네이버의 뉴스 검색 API를 통해 한국어 뉴스 기사를 수집합니다.
   - 설정: `.env` 파일에 `NAVER_CLIENT_ID`와 `NAVER_CLIENT_SECRET` 값 필요

### 뉴스 소스 동작 방식

- 모든 활성화된 뉴스 소스에서 병렬로 기사를 수집합니다.
- 중복된 기사는 URL과 제목을 기준으로 자동 제거됩니다.
- 각 소스에서 최대 10개(기본값)의 기사를 수집하며, 명령줄 인수로 조정 가능합니다.

## 핵심 기능 설명

### 1. 기사 필터링 시스템

- **중복 제거**: URL 및 제목을 기반으로 중복된 기사를 식별하고 제거합니다.
- **주요 소스 우선순위**: 주요 언론사(조선일보, 중앙일보 등)와 기타 소스를 티어로 구분하여 신뢰할 수 있는 주요 소스의 기사를 우선적으로 표시합니다.
- **도메인 다양성**: 특정 출처의 기사가 과도하게 많아지는 것을 방지하기 위해 도메인별 최대 기사 수를 제한합니다.

### 2. 키워드 그룹화

- **정확 일치**: 키워드와 정확히 일치하는 기사를 그룹화
- **공백 무시 매칭**: 키워드 내 공백 유무와 관계없이 매칭 (예: "AI반도체" = "AI 반도체")
- **부분 일치**: 복합 키워드의 경우 구성 단어들이 기사 내에 존재하는지 확인

### 3. 핵심 뉴스 선별
- 기사 중요도를 계산하여 가장 중요한 3개 기사를 별도로 표시합니다. 상단 "핵심 뉴스 TOP 3" 영역에서 확인할 수 있습니다.

### 4. 자동 키워드 생성

- Gemini Pro AI를 활용하여 특정 도메인에 대한 관련 키워드를 자동으로 생성합니다.
- 생성된 키워드를 기반으로 뉴스를 수집하고 요약합니다.

### 5. 테스트 모드

- **Template 모드**: HTML 템플릿 변경 테스트에 유용합니다. 기존 데이터를 새 템플릿으로 빠르게 재렌더링합니다.
- **Content 모드**: 동일한 기사 데이터로 다양한 처리/요약 방식을 테스트할 수 있습니다. 기사 수집 단계를 건너뛰고 처리/요약 프로세스만 실행합니다.

---

## 개발자를 위한 CI/CD 정보

### 🔄 GitHub Actions 워크플로우

이 프로젝트는 다음과 같은 GitHub Actions 워크플로우를 사용합니다:

#### 1. CI 워크플로우 (`.github/workflows/ci.yml`)
- **트리거**: main 브랜치 push, Pull Request
- **Python 버전**: 3.10, 3.11 매트릭스 테스트
- **단계**:
  - 최소 의존성으로 빠른 테스트 실행
  - Black 코드 포맷팅 검사
  - 외부 의존성 없는 기본 테스트 실행
  - 통합 테스트 (mocked APIs)

#### 2. 코드 품질 워크플로우 (`.github/workflows/code-quality.yml`)
- **트리거**: main 브랜치 push, Pull Request
- **검사 항목**:
  - Black 코드 포맷팅
  - isort import 정렬
  - flake8 린팅
  - mypy 타입 검사 (선택적)

#### 3. 도구 테스트 워크플로우 (`.github/workflows/test-tools.yml`)
- **트리거**: 특정 파일 변경 시 (`newsletter/tools.py`, `tests/test_tools.py`, `requirements.txt`)
- **기능**: 도구 모듈의 import 및 기본 기능 테스트

#### 4. 뉴스레터 생성 워크플로우 (`.github/workflows/newsletter.yml`)
- **트리거**: 스케줄 (매일 UTC 23:00), 수동 실행
- **기능**: 실제 뉴스레터 생성 및 GitHub Pages 배포

### 📦 의존성 관리

프로젝트는 다음과 같은 의존성 파일을 사용합니다:

- `requirements.txt`: 전체 프로덕션 의존성
- `requirements-dev.txt`: 개발 및 테스트 도구
- `requirements-minimal.txt`: CI에서 빠른 테스트를 위한 최소 의존성
- `pyproject.toml`: 현대적인 Python 패키징 설정

### 🧪 로컬 개발 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/newsletter-generator.git
cd newsletter-generator

# 2. 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 또는
.venv\Scripts\activate     # Windows

# 3. 개발 의존성 설치
pip install -r requirements-dev.txt
pip install -e .

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 API 키 설정

# 5. 테스트 실행
python run_tests.py dev
```

### 🔧 코드 품질 도구

프로젝트는 다음 도구들을 사용하여 코드 품질을 유지합니다:

```bash
# 코드 포맷팅
black newsletter tests

# Import 정렬
isort newsletter tests

# 린팅
flake8 newsletter tests

# 타입 검사
mypy newsletter
```

### 📋 Pull Request 체크리스트

Pull Request를 생성하기 전에 다음을 확인하세요:

- [ ] 모든 테스트가 통과하는지 확인: `python run_tests.py ci`
- [ ] 코드 포맷팅이 올바른지 확인: `black --check newsletter tests`
- [ ] 새로운 기능에 대한 테스트 추가
- [ ] 문서 업데이트 (필요한 경우)
- [ ] CHANGELOG.md 업데이트 (필요한 경우)

### 🚀 배포 프로세스

1. **개발**: feature 브랜치에서 개발
2. **테스트**: `python run_tests.py ci`로 로컬 검증
3. **Pull Request**: main 브랜치로 PR 생성
4. **CI 검증**: GitHub Actions에서 자동 테스트 실행
5. **코드 리뷰**: 팀원 리뷰 후 승인
6. **병합**: main 브랜치로 병합
7. **자동 배포**: GitHub Pages로 자동 배포

### 🔍 디버깅 및 문제 해결

#### CI 실패 시 확인사항:
1. 로컬에서 동일한 Python 버전으로 테스트
2. 의존성 버전 충돌 확인
3. 환경 변수 설정 확인
4. 테스트 데이터 및 모킹 설정 확인

#### 일반적인 문제:
- **gRPC 오류**: 환경 변수 `GOOGLE_API_USE_REST=true` 설정
- **의존성 충돌**: `pip install --upgrade pip` 후 재설치
- **테스트 타임아웃**: 네트워크 연결 및 API 응답 시간 확인

---

### 문서 버전 기록

| 버전 | 일자       | 작성자         | 변경 요약                                                       |
| ---- | ---------- | -------------- | --------------------------------------------------------------- |
| 0.7  | 2025-05-24 | Hojung Jung    | 환경별 테스트 전략 도입 및 통합 테스트 스크립트 구현                |
| 0.6  | 2025-05-22 | Hojung Jung    | 테스트 모드 기능 추가 (template/content)                             |
| 0.5  | 2025-05-13 | Hojung Jung    | 기사 필터링 및 그룹화 기능 추가                                     |
| 0.4  | 2025‑05‑11 | Hojung Jung    | 다양한 뉴스 소스 통합 기능 반영 (RSS, 네이버 API)                    |
| 0.3  | 2025‑05‑09 | Hojung Jung    | LangChain/LangGraph 통합 반영, 관련 문서 업데이트                   |
| 0.2  | 2025‑05‑09 | Hojung Jung    | MVP 범위 이메일 발송 반영, LLM → Gemini Pro, 대상 → 내부 연구원      |
| 0.1  | 2025‑05‑09 | Hojung Jung    | 초기 초안                                                        |
