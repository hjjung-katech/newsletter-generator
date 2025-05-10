# Newsletter Generator

## 개요

Newsletter Generator는 내부 연구원이 입력(또는 자동 추천)한 키워드를 기반으로 최신 뉴스를 수집‧요약하여 이메일로 발송하고, 필요 시 Google Drive에 저장하는 Python CLI 도구입니다.

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
```

### 환경 설정

`.env` 파일을 프로젝트 루트 디렉터리에 생성하고 다음과 같이 API 키를 설정하세요:

```
# 뉴스 수집용 API 키
NEWS_API_KEY=your_news_api_key
SERPER_API_KEY=your_serper_api_key

# 생성형 AI 요약용 API 키
GEMINI_API_KEY=your_gemini_api_key

# 이메일 발송용 API 키 (선택사항)
SENDGRID_API_KEY=your_sendgrid_api_key

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

**기존 방식: `--keywords` 옵션으로 직접 키워드 지정하여 뉴스레터 생성**

```bash
# 키워드로 뉴스 검색 및 뉴스레터 생성
newsletter run --keywords "자율주행,ADAS" --output-format html
```

### 주요 명령어 옵션

**`newsletter run` 명령어 옵션:**

| 옵션 | 설명 | 기본값 |
|-----|-----|-----|
| `--keywords` | 검색할 키워드 (쉼표로 구분). `--domain`이 제공되지 않거나 키워드 생성 실패 시 사용됩니다. | 없음 |
| `--domain` | 키워드를 생성할 분야. 이 옵션 사용 시 `--keywords`는 무시될 수 있습니다 (키워드 생성 실패 시 제외). | 없음 |
| `--suggest-count` | `--domain` 사용 시 생성할 키워드 개수. | 10 |
| `--to` | 뉴스레터를 발송할 이메일 주소 | 없음 (이메일 발송 건너뜀) |
| `--output-format` | 로컬에 저장할 형식 (html 또는 md) | 지정하지 않으면 `--drive` 옵션 시 Drive에만 저장, 아니면 html로 로컬 저장 |
| `--drive` | Google Drive에 저장할지 여부 | False |
| `--use-langgraph` | LangGraph 워크플로우 사용 여부 (권장) | True |

**`newsletter suggest` 명령어 옵션:**

| 옵션 | 설명 | 기본값 |
|-----|-----|-----|
| `--domain` | 추천 키워드를 생성할 분야 (필수) | - |
| `--count` | 생성할 키워드 개수 | 10 |

---

### 단위 테스트 실행

프로젝트의 단위 테스트를 실행하려면 다음 명령을 사용하세요:

```bash
python -m unittest discover -s ./tests -p "test_*.py"
```

이 명령은 `tests` 디렉토리 내의 `test_*.py` 패턴과 일치하는 모든 테스트 파일을 찾아 실행합니다.

---

### 문서 버전 기록

| 버전  | 일자         | 작성자     | 변경 요약                                           |
| --- | ---------- | ------- | ----------------------------------------------- |
| 0.3 | 2025‑05‑09 | GitHub Copilot | LangChain/LangGraph 통합 반영, 관련 문서 업데이트 |
| 0.2 | 2025‑05‑09 | ChatGPT | MVP 범위 이메일 발송 반영, LLM → Gemini Pro, 대상 → 내부 연구원 |
| 0.1 | 2025‑05‑09 | ChatGPT | 초기 초안                                           |
