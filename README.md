# Newsletter Generator

## 최근 업데이트: 필터링 기능 추가

최근 시스템에 다음과 같은 필터링 기능이 추가되었습니다:

- **중복 기사 감지 및 제거**: URL 및 제목 기반으로 중복 기사 필터링
- **주요 뉴스 소스 우선순위**: 티어 시스템을 적용하여 신뢰할 수 있는 소스 우선 표시
- **도메인 다양성 보장**: 특정 출처에 편중되지 않도록 도메인별 기사 수 제한
- **키워드별 기사 그룹화**: 다양한 매칭 알고리즘을 적용한 효과적인 그룹화

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
```

### 사용 방법

뉴스레터를 생성하는 방법은 두 가지가 있습니다.

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
```

**3. 직접 키워드 지정 및 필터링 옵션 활용**

```bash
# 키워드로 뉴스 검색 및 뉴스레터 생성
newsletter run --keywords "자율주행,ADAS" --output-format html

# 필터링 옵션 적용 (중복 제거, 키워드별 그룹화, 주요 소스 우선 처리)
newsletter run --keywords "AI반도체,HBM" --max-per-source 3 --output-format html 

# 특정 필터링 기능 비활성화
newsletter run --keywords "메타버스,XR" --no-filter-duplicates --no-major-sources-filter --output-format html
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

### 3. 자동 키워드 생성

- Gemini Pro AI를 활용하여 특정 도메인에 대한 관련 키워드를 자동으로 생성합니다.
- 생성된 키워드를 기반으로 뉴스를 수집하고 요약합니다.

---

## 개발 가이드

### 코드 포맷팅

이 프로젝트는 [Black](https://github.com/psf/black) 코드 포맷터를 사용하여 일관된 코드 스타일을 유지합니다:

```bash
# Black 설치
pip install black

# 코드 포맷팅 실행
black newsletter
black tests
```

자동화된 포맷팅 검사를 위해 다음 명령어를 사용할 수 있습니다:

```bash
# 코드 포맷팅 검사 실행
python run_tests.py --format-only

# 코드 포맷팅 후 테스트 실행
python run_tests.py --format --all
```

## 테스트

### 테스트 구조

프로젝트 테스트는 `tests` 디렉토리에 체계적으로 관리되며 다음과 같은 구조로 되어 있습니다:

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

### 테스트 실행

테스트 자동화 스크립트를 사용하여 쉽게 테스트를 실행할 수 있습니다:

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

### 테스트 유형

프로젝트는 다음과 같은 테스트 유형을 포함하고 있습니다:

1. **필터링 및 그룹화 테스트**
   - 중복 기사 감지, 키워드 그룹화, 소스 우선순위 지정 등 테스트
   - 주요 파일: `test_article_filter.py`, `api_tests/test_article_filter_integration.py`

2. **API 및 검색 테스트**
   - 외부 API 연동 및 검색 기능 테스트
   - 주요 파일: `test_serper_api.py`, `api_tests/test_serper_direct.py`, `api_tests/test_sources.py`

3. **날짜 처리 테스트**
   - 날짜 파싱, 포맷팅, 주 단위 계산 등 테스트
   - 주요 파일: `test_graph_date_parser.py`, `unit_tests/test_date_utils.py`, `unit_tests/test_weeks_ago.py`

4. **뉴스레터 생성 테스트**
   - 전체 뉴스레터 생성 과정 테스트
   - 주요 파일: `test_newsletter.py`, `unit_tests/test_new_newsletter.py`

자세한 테스트 정보와 모든 테스트 파일 목록은 [tests/README.md](tests/README.md) 파일을 참조하세요.

---

## VS Code 개발 환경 설정

이 프로젝트는 Visual Studio Code를 위한 개발 환경 설정을 포함하고 있습니다. 설정 파일은 `.vscode` 폴더에 위치하며 다음과 같은 기능을 제공합니다:

### 자동 환경 설정

- `settings.json`: Python 인터프리터 설정과 Conda/가상환경 자동 활성화 등 설정
- `launch.json`: 테스트 실행, 디버깅 구성 설정
- `tasks.json`: 코드 포맷팅, 테스트 실행 등을 위한 작업 정의
- `extensions.json`: 프로젝트에 권장되는 VS Code 확장 프로그램 목록

### 사용 방법

1. Visual Studio Code에서 프로젝트 폴더를 엽니다.
2. 터미널은 자동으로 Python 가상환경을 활성화합니다.
3. 디버그 패널(F5)에서 테스트 실행 구성을 선택할 수 있습니다.
4. 명령 팔레트(Ctrl+Shift+P)에서 "Tasks: Run Task"를 선택하여 정의된 작업을 실행할 수 있습니다.

### 환경 설정 커스터마이징

각 개발자의 로컬 환경에 맞게 설정을 변경해야 할 경우:

1. Conda 환경 이름 변경: `.vscode/settings.json` 파일에서 `newsletter-env` 부분을 변경
2. 가상 환경 경로 변경: 기본적으로 `.venv` 폴더를 사용하도록 설정되어 있으며, 필요시 변경

## 향후 개선 사항

1. **필터링 정확도 향상**
   - 동의어 사전 추가로 다양한 표현 인식 개선
   - 맥락 기반 매칭으로 연관성 높은 기사 선별
   - NLP 기법을 활용한 의미론적 유사성 검출

2. **성능 최적화**
   - 대규모 기사 집합에 대한 문자열 매칭 알고리즘 개선
   - 자주 액세스하는 주요 소스에 대한 캐싱 추가

3. **언어 지원 강화**
   - 다국어 콘텐츠 처리 확장
   - 한국어/영어 혼합 콘텐츠 처리 개선

---

### 문서 버전 기록

| 버전 | 일자       | 작성자         | 변경 요약                                                       |
| ---- | ---------- | -------------- | --------------------------------------------------------------- |
| 0.5  | 2025-05-13 | Claude         | 기사 필터링 및 그룹화 기능 추가                                 |
| 0.4  | 2025‑05‑11 | Claude         | 다양한 뉴스 소스 통합 기능 반영 (RSS, 네이버 API)               |
| 0.3  | 2025‑05‑09 | GitHub Copilot | LangChain/LangGraph 통합 반영, 관련 문서 업데이트               |
| 0.2  | 2025‑05‑09 | ChatGPT        | MVP 범위 이메일 발송 반영, LLM → Gemini Pro, 대상 → 내부 연구원 |
| 0.1  | 2025‑05‑09 | ChatGPT        | 초기 초안                                                       |
