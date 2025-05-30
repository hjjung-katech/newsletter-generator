# CLI 참조 가이드

Newsletter Generator의 모든 CLI 명령어와 옵션에 대한 상세한 참조 문서입니다.

## 📋 목차

1. [기본 구조](#기본-구조)
2. [newsletter run](#newsletter-run)
3. [newsletter suggest](#newsletter-suggest)
4. [newsletter test](#newsletter-test)
5. [newsletter test-email](#newsletter-test-email)
6. [전역 옵션](#전역-옵션)
7. [환경 변수](#환경-변수)
8. [예시 모음](#예시-모음)

## 기본 구조

```bash
newsletter [COMMAND] [OPTIONS]
```

### 사용 가능한 명령어

| 명령어 | 설명 |
|--------|------|
| `run` | 뉴스레터 생성 및 발송 |
| `suggest` | 키워드 추천 |
| `test` | 기존 데이터로 테스트 |
| `test-email` | 이메일 발송 기능 테스트 |

## newsletter run

뉴스레터를 생성하고 발송하는 메인 명령어입니다.

### 기본 문법

```bash
newsletter run [OPTIONS]
```

### 필수 옵션 (둘 중 하나 선택)

| 옵션 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `--keywords` | TEXT | 검색할 키워드 (쉼표로 구분) | `--keywords "AI,머신러닝,딥러닝"` |
| `--domain` | TEXT | 키워드를 생성할 분야 | `--domain "자율주행 기술"` |

### 기본 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--suggest-count` | INTEGER | 10 | `--domain` 사용 시 생성할 키워드 개수 |
| `--period`, `-p` | INTEGER | 14 | 최신 뉴스 수집 기간(일 단위) |
| `--template-style` | CHOICE | detailed | 템플릿 스타일 (`compact` 또는 `detailed`) |
| `--email-compatible` | FLAG | False | 이메일 클라이언트 호환 템플릿 사용 |

### 출력 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--output-format` | CHOICE | html | 로컬 저장 형식 (`html` 또는 `md`) |
| `--to` | TEXT | - | 뉴스레터를 발송할 이메일 주소 |
| `--drive` | FLAG | False | Google Drive에 뉴스레터 저장 |

### 필터링 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--max-per-source` | INTEGER | - | 도메인별 최대 기사 수 |
| `--no-filter-duplicates` | FLAG | False | 중복 기사 필터링 비활성화 |
| `--no-major-sources-filter` | FLAG | False | 주요 뉴스 소스 우선순위 비활성화 |
| `--no-group-by-keywords` | FLAG | False | 키워드별 기사 그룹화 비활성화 |

### 고급 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--track-cost` | FLAG | False | LangSmith 비용 추적 활성화 |
| `--save-intermediate` | FLAG | False | 중간 처리 결과 저장 |
| `--verbose`, `-v` | FLAG | False | 상세한 로그 출력 |

### 사용 예시

```bash
# 기본 사용법
newsletter run --keywords "AI,머신러닝" --output-format html

# 도메인 기반 키워드 생성
newsletter run --domain "자율주행" --suggest-count 5 --to user@example.com

# 필터링 옵션 적용
newsletter run --keywords "반도체,HBM" --max-per-source 3 --no-filter-duplicates

# 모든 옵션 사용
newsletter run \
  --domain "인공지능" \
  --suggest-count 7 \
  --period 7 \
  --template-style compact \
  --to user@example.com \
  --drive \
  --output-format html \
  --max-per-source 5 \
  --track-cost \
  --verbose
```

## newsletter suggest

특정 도메인에 대한 키워드를 추천받는 명령어입니다.

### 기본 문법

```bash
newsletter suggest [OPTIONS]
```

### 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--domain` | TEXT | - | 추천 키워드를 생성할 분야 (필수) |
| `--count` | INTEGER | 10 | 생성할 키워드 개수 |

### 사용 예시

```bash
# 기본 키워드 추천
newsletter suggest --domain "자율주행"

# 키워드 개수 지정
newsletter suggest --domain "배터리 기술" --count 15

# 추천 결과를 파일로 저장
newsletter suggest --domain "AI" --count 20 > keywords.txt
```

### 출력 형식

```
Suggested keywords for domain "자율주행":
1. 자율주행차
2. ADAS
3. 라이다
4. 카메라 센서
5. 자율주행 레벨
...

To generate a newsletter with these keywords, you can use the following command:
newsletter run --keywords "자율주행차,ADAS,라이다,카메라 센서,자율주행 레벨" --output-format html
```

## newsletter test

기존 데이터를 사용하여 테스트를 수행하는 명령어입니다.

### 기본 문법

```bash
newsletter test [DATA_FILE] [OPTIONS]
```

### 위치 인수

| 인수 | 타입 | 설명 |
|------|------|------|
| `DATA_FILE` | PATH | 테스트에 사용할 데이터 파일 경로 (필수) |

### 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--mode` | CHOICE | template | 실행 모드 (`template` 또는 `content`) |
| `--output` | PATH | - | 생성된 뉴스레터의 출력 파일 경로 |
| `--track-cost` | FLAG | False | LangSmith 비용 추적 활성화 |

### 테스트 모드

#### Template 모드

기존 뉴스레터 데이터를 현재 HTML 템플릿으로 재렌더링합니다.

- **용도**: 템플릿 변경 테스트
- **입력 파일**: `render_data_*.json`
- **처리 과정**: 템플릿 렌더링만 수행

```bash
newsletter test output/render_data_20250522_143255.json --mode template
```

#### Content 모드

이전에 수집된 기사 데이터로 전체 프로세스를 재실행합니다.

- **용도**: 처리/요약 로직 테스트
- **입력 파일**: `collected_articles_*.json`
- **처리 과정**: 수집 단계를 제외한 모든 프로세스

```bash
newsletter test output/collected_articles_AI.json --mode content
```

### 사용 예시

```bash
# Template 모드 기본 사용
newsletter test output/render_data_20250522_143255.json --mode template

# Content 모드 with 비용 추적
newsletter test output/collected_articles_AI.json --mode content --track-cost

# 커스텀 출력 파일 지정
newsletter test data.json --mode template --output custom_newsletter.html
```

## newsletter test-email

이메일 발송 기능만 단독으로 테스트하는 명령어입니다. 뉴스레터 생성 없이 Postmark 이메일 발송 설정을 확인하고 테스트할 수 있습니다.

### 기본 문법

```bash
newsletter test-email [OPTIONS]
```

### 필수 옵션

| 옵션 | 타입 | 설명 |
|------|------|------|
| `--to` | TEXT | 테스트 이메일을 받을 이메일 주소 (필수) |

### 선택적 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--subject` | TEXT | 자동 생성 | 이메일 제목 (미지정 시 타임스탬프 포함 기본 제목) |
| `--template` | PATH | - | 이메일 내용으로 사용할 HTML 파일 경로 |
| `--dry-run` | FLAG | False | 실제 발송 없이 설정 확인만 수행 |

### 기능 설명

#### 기본 테스트 모드

템플릿을 지정하지 않으면 기본 테스트 메시지를 발송합니다:

- 📧 이메일 발송 성공 확인 메시지
- 📋 테스트 정보 (발송 시간, 수신자, 서비스 정보)
- 🔧 다음 단계 안내
- 깔끔한 HTML 디자인

#### 커스텀 템플릿 모드

기존 HTML 파일을 이메일 내용으로 사용할 수 있습니다:

- 생성된 뉴스레터 파일 테스트
- 커스텀 HTML 템플릿 테스트
- 이메일 렌더링 확인

#### Dry Run 모드

실제 이메일을 발송하지 않고 설정만 확인합니다:

- Postmark 토큰 설정 확인
- 발송자 이메일 설정 확인
- 이메일 내용 길이 확인
- 설정 문제 진단

### 사용 예시

#### 기본 테스트

```bash
# 기본 테스트 메시지 발송
newsletter test-email --to user@example.com

# 커스텀 제목으로 테스트
newsletter test-email --to user@example.com --subject "내 이메일 테스트"
```

#### 템플릿 테스트

```bash
# 기존 뉴스레터 파일로 테스트
newsletter test-email --to user@example.com --template output/newsletter.html

# 커스텀 HTML 파일로 테스트
newsletter test-email --to user@example.com --template my_template.html --subject "템플릿 테스트"
```

#### 설정 확인

```bash
# 실제 발송 없이 설정만 확인
newsletter test-email --to user@example.com --dry-run

# 템플릿과 함께 설정 확인
newsletter test-email --to user@example.com --template newsletter.html --dry-run
```

### 출력 예시

#### 성공적인 발송

```
Testing email sending to: user@example.com
📤 이메일 발송 중...
발송자: newsletter@company.com
수신자: user@example.com
제목: Newsletter Generator 이메일 테스트 - 2025-01-26 10:30:15

✅ 이메일이 성공적으로 발송되었습니다!
수신자 user@example.com의 받은편지함을 확인해주세요.
테스트 이메일 내용이 저장되었습니다: output/test_email_20250126_103015.html
```

#### Dry Run 결과

```
🔍 DRY RUN MODE - 실제 이메일은 발송되지 않습니다
수신자: user@example.com
제목: Newsletter Generator 이메일 테스트 - 2025-01-26 10:30:15
내용 길이: 2847 문자
Postmark 토큰 설정 여부: ✅ 설정됨
발송자 이메일: newsletter@company.com

Dry run 완료. 실제 발송하려면 --dry-run 옵션을 제거하세요.
```

#### 설정 오류

```
❌ POSTMARK_SERVER_TOKEN이 설정되지 않았습니다.
이메일 발송을 위해 .env 파일에 다음을 설정해주세요:
POSTMARK_SERVER_TOKEN=your_postmark_server_token
EMAIL_SENDER=your_verified_sender@example.com
```

### 문제 해결

#### 1. Postmark 설정 확인

```bash
# 설정 상태 확인
newsletter test-email --to test@example.com --dry-run

# 환경 변수 확인
echo "POSTMARK_SERVER_TOKEN: ${POSTMARK_SERVER_TOKEN:0:10}..."
echo "EMAIL_SENDER: $EMAIL_SENDER"
```

#### 2. 템플릿 파일 문제

```bash
# 파일 존재 확인
ls -la output/newsletter.html

# 파일 내용 확인
head -20 output/newsletter.html
```

#### 3. 네트워크 연결 확인

```bash
# Postmark API 연결 테스트
curl -H "X-Postmark-Server-Token: YOUR_TOKEN" https://api.postmarkapp.com/server
```

#### 4. Postmark API 오류 해결

**422 오류 (비활성 수신자)**
```
Error sending email: 422 {"ErrorCode":406,"Message":"You tried to send to recipient(s) that have been marked as inactive..."}
```
- 원인: 수신자가 하드 바운스, 스팸 신고, 수동 차단됨
- 해결: 다른 이메일 주소로 테스트

**401 오류 (인증 실패)**
```
Error sending email: 401 Unauthorized
```
- 원인: 잘못된 서버 토큰
- 해결: Postmark 대시보드에서 토큰 재확인

**403 오류 (권한 없음)**
```
Error sending email: 403 Forbidden
```
- 원인: 계정 승인 대기 중
- 해결: 같은 도메인 내 이메일 주소로만 테스트 가능

## 전역 옵션

모든 명령어에서 사용할 수 있는 옵션들입니다.

| 옵션 | 설명 |
|------|------|
| `--help` | 도움말 표시 |
| `--version` | 버전 정보 표시 |

### 사용 예시

```bash
# 전체 도움말
newsletter --help

# 특정 명령어 도움말
newsletter run --help
newsletter suggest --help
newsletter test --help

# 버전 확인
newsletter --version
```

## 환경 변수

CLI에서 사용하는 주요 환경 변수들입니다.

### 필수 환경 변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `GEMINI_API_KEY` | Google Gemini Pro API 키 | `AIza...` |
| `SERPER_API_KEY` | Serper.dev API 키 | `abc123...` |

### 선택적 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `NAVER_CLIENT_ID` | 네이버 뉴스 API 클라이언트 ID | - |
| `NAVER_CLIENT_SECRET` | 네이버 뉴스 API 클라이언트 시크릿 | - |
| `POSTMARK_SERVER_TOKEN` | Postmark 서버 토큰 (이메일 발송용) | - |
| `EMAIL_SENDER` | 발송자 이메일 주소 (Postmark에서 인증 필요) | - |
| `GOOGLE_CLIENT_ID` | Google Drive API 클라이언트 ID | - |
| `GOOGLE_CLIENT_SECRET` | Google Drive API 클라이언트 시크릿 | - |
| `LANGCHAIN_API_KEY` | LangSmith API 키 | - |
| `LANGCHAIN_TRACING_V2` | LangSmith 추적 활성화 | `false` |
| `LANGCHAIN_PROJECT` | LangSmith 프로젝트 이름 | - |
| `ADDITIONAL_RSS_FEEDS` | 추가 RSS 피드 URL (쉼표 구분) | - |

### 환경 변수 설정 방법

#### .env 파일 사용 (권장)

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
```

#### 직접 설정

```bash
# Linux/Mac
export GEMINI_API_KEY="your_api_key"
export SERPER_API_KEY="your_api_key"

# Windows
set GEMINI_API_KEY=your_api_key
set SERPER_API_KEY=your_api_key
```

## 예시 모음

### 일반적인 사용 시나리오

#### 1. 빠른 뉴스레터 생성

```bash
# 가장 간단한 사용법
newsletter run --keywords "AI" --output-format html
```

#### 2. 이메일 발송 포함

```bash
# 생성 후 즉시 이메일 발송
newsletter run --keywords "자율주행,ADAS" --to manager@company.com
```

#### 3. 도메인 기반 자동 생성

```bash
# 키워드 자동 생성 후 뉴스레터 생성
newsletter run --domain "친환경 자동차" --suggest-count 8 --output-format html
```

#### 4. 고품질 필터링

```bash
# 엄격한 필터링으로 고품질 뉴스레터
newsletter run --keywords "반도체,HBM" --max-per-source 2 --period 7
```

#### 5. 간결한 임원용 리포트

```bash
# Compact 스타일로 간결한 리포트
newsletter run --domain "AI" --template-style compact --to ceo@company.com
```

### 고급 사용 시나리오

#### 1. 비용 추적과 함께

```bash
# LangSmith로 비용 추적
newsletter run --keywords "AI,머신러닝" --track-cost --output-format html
```

#### 2. 배치 처리

```bash
# 여러 도메인을 순차 처리
domains=("AI" "자율주행" "반도체" "배터리")
for domain in "${domains[@]}"; do
    newsletter run --domain "$domain" --template-style compact --drive
done
```

#### 3. 테스트 및 디버깅

```bash
# 상세 로그와 중간 결과 저장
newsletter run --keywords "AI" --verbose --save-intermediate

# 기존 데이터로 템플릿 테스트
newsletter test output/render_data_latest.json --mode template --output test.html

# 이메일 발송 기능 테스트
newsletter test-email --to admin@company.com --dry-run
newsletter test-email --to admin@company.com --template output/newsletter.html
```

#### 4. 커스터마이징된 필터링

```bash
# 특정 필터링만 적용
newsletter run --keywords "블록체인,NFT" \
  --no-filter-duplicates \
  --max-per-source 5 \
  --period 3
```

### 에러 처리 및 복구

#### 1. API 키 확인

```bash
# 환경 변수 확인
echo "GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}..."
echo "SERPER_API_KEY: ${SERPER_API_KEY:0:10}..."
```

#### 2. 네트워크 문제 해결

```bash
# 최소한의 요청으로 테스트
newsletter run --keywords "AI" --max-per-source 1 --period 1
```

#### 3. 메모리 부족 해결

```bash
# 리소스 사용량 최소화
newsletter run --keywords "AI" \
  --template-style compact \
  --max-per-source 3 \
  --period 3 \
  --no-group-by-keywords
```

## 종료 코드

CLI 명령어의 종료 코드 의미:

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 일반적인 오류 |
| 2 | 잘못된 인수 또는 옵션 |
| 3 | API 키 오류 |
| 4 | 네트워크 오류 |
| 5 | 파일 I/O 오류 |

## 추가 리소스

- [사용자 가이드](USER_GUIDE.md) - 상세한 사용법과 개념 설명
- [예시 모음](EXAMPLES.md) - 다양한 시나리오별 예시
- [FAQ](FAQ.md) - 자주 묻는 질문과 해결책
- [설정 가이드](../setup/CONFIGURATION.md) - 환경 변수 및 설정 상세 가이드 