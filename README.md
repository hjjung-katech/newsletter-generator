# Newsletter Generator

[![CI/CD Pipeline](https://github.com/hjjung-katech/newsletter-generator/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/ci.yml)
[![Code Quality](https://github.com/hjjung-katech/newsletter-generator/workflows/Code%20Quality/badge.svg)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/code-quality.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Deploy on Railway](https://railway.app/button.svg)](https://newsletter-generator-production-73b6.up.railway.app/)

**Newsletter Generator**는 키워드 기반으로 최신 뉴스를 수집·요약하여 HTML 뉴스레터를 생성하고 이메일로 발송하는 Python CLI 도구입니다.

## 🚀 주요 기능

- 🔍 **다양한 뉴스 소스**: Serper API, RSS 피드, 네이버 뉴스 API 통합
- 🤖 **멀티 LLM 지원**: Google Gemini, OpenAI GPT, Anthropic Claude 모델 통합 지원
- 🎛️ **기능별 LLM 설정**: 키워드 생성, 요약, HTML 생성 등 기능별로 다른 LLM 모델 사용 가능
- 📧 **자동 발송**: Postmark를 통한 이메일 발송 및 Google Drive 저장
- 🎯 **스마트 필터링**: 중복 제거, 주요 소스 우선순위, 키워드별 그룹화
- 📱 **두 가지 스타일**: Compact(간결) / Detailed(상세) 뉴스레터 지원
- 📧 **이메일 호환성**: 모든 이메일 클라이언트에서 완벽 렌더링되는 Email-Compatible 템플릿 지원
- 💰 **비용 추적**: 제공자별 토큰 사용량 및 비용 자동 추적
- 🌐 **웹 인터페이스**: Flask 기반 웹 애플리케이션 제공
- ⏰ **정기 발송**: RRULE 기반 스케줄링으로 정기적인 뉴스레터 발송
- ☁️ **클라우드 배포**: Railway PaaS 원클릭 배포 지원
- 🔧 **Mock Mode**: 개발 및 테스트를 위한 Mock 데이터 지원
- 📊 **Health Check**: 시스템 상태 및 의존성 모니터링
- 🚨 **통합 모니터링**: Sentry를 통한 에러 추적 및 성능 모니터링
- 📝 **구조화 로깅**: JSON 포맷 로깅으로 운영 환경 모니터링 최적화

## 🚀 Railway 클라우드 배포

### 원클릭 배포

[![Deploy on Railway](https://railway.app/button.svg)](https://newsletter-generator-production-73b6.up.railway.app/)

### 수동 배포

1. **Repository 연결**
   ```bash
   git clone https://github.com/hjjung-katech/newsletter-generator.git
   cd newsletter-generator
   ```

2. **Railway CLI 설치**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

3. **프로젝트 생성 및 배포**
   ```bash
   railway deploy
   ```

4. **환경변수 설정**
   Railway 대시보드에서 다음 환경변수를 설정하세요:
   ```
   # 필수 API 키
   SERPER_API_KEY=your_serper_key_here
   OPENAI_API_KEY=sk-...
   
   # 이메일 발송 (Postmark)
   POSTMARK_SERVER_TOKEN=your_postmark_token
   EMAIL_SENDER=newsletter@yourdomain.com
   
   # 웹 애플리케이션
   SECRET_KEY=your-secret-key-here
   FLASK_ENV=production
   PORT=8080
   
   # 선택사항 - 모니터링
   SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
   LOG_LEVEL=INFO
   
   # 개발/테스트 모드 (운영환경에서는 false)
   MOCK_MODE=false
   ```

### 서비스 구성

Railway에서는 다음 4개 서비스가 자동으로 배포됩니다:

- **web**: Flask 웹 애플리케이션 (메인 API 서버)
- **worker**: Redis-RQ 백그라운드 워커 (뉴스레터 생성)
- **scheduler**: RRULE 기반 스케줄 실행기 (정기 발송)
- **redis**: Redis 인스턴스 (작업 큐 및 캐시)

### 배포 후 테스트

```bash
# 로컬에서 배포된 서비스 테스트
python test_railway.py --url https://your-app.railway.app

# Health Check 엔드포인트 확인
curl https://your-app.railway.app/health

# 뉴스레터 생성 테스트 (Mock 모드가 비활성화된 상태)
curl "https://your-app.railway.app/newsletter?period=7&keywords=AI,tech"

# 또는 환경변수 설정 후
export RAILWAY_PRODUCTION_URL=https://your-app.railway.app
python test_railway.py --production
```

자세한 배포 가이드는 [Railway 배포 문서](docs/setup/RAILWAY_DEPLOYMENT.md)를 참고하세요.

## 🚀 빠른 시작

### 1. 환경 설정

**자동 설정 (추천):**
```bash
python setup_env.py
```

**수동 설정:**
1. `.env` 파일을 루트 디렉토리에 생성
2. 필수 환경변수 설정:

```env
# 필수 API 키
SERPER_API_KEY=your_serper_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# 이메일 발송 (필수 - 이메일 기능 사용시)
POSTMARK_SERVER_TOKEN=your_postmark_server_token_here
EMAIL_SENDER=your_verified_email@yourdomain.com

# 웹 애플리케이션
SECRET_KEY=your-secret-key-here

# 선택사항 - 추가 기능
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 모니터링 (선택사항)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# 개발/테스트 모드
MOCK_MODE=false  # 운영환경에서는 false, 개발시에는 true
```

### 2. API 키 발급 방법

#### 🔍 Serper API (필수 - 뉴스 검색)
- https://serper.dev 방문
- 구글 계정으로 로그인
- Dashboard에서 API 키 발급
- 월 2,500회 무료 사용 가능

#### 🤖 Google Gemini API (필수 - AI 처리)
- https://aistudio.google.com 방문
- Google 계정으로 로그인
- 'Get API Key' 클릭하여 발급
- 무료 할당량 제공

#### 📧 Postmark (필수 - 이메일 발송)
- https://postmarkapp.com 방문
- 계정 생성 (월 100개 이메일 무료)
- Server Token 발급 후 POSTMARK_SERVER_TOKEN에 설정
- Signatures에서 발송자 이메일 인증 필수

#### 🤖 OpenAI API (선택사항항 - AI 처리)
- https://platform.openai.com 방문
- API 키 발급 후 OPENAI_API_KEY에 설정
- 사용량에 따른 과금

#### 🚨 Sentry (선택사항 - 에러 모니터링)
- https://sentry.io 방문
- 프로젝트 생성 후 DSN 확인
- SENTRY_DSN에 설정하면 자동으로 에러 추적 활성화

### 3. 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 이메일 발송 테스트
python -m newsletter test-email --to your@email.com

# 뉴스레터 생성
python -m newsletter run --keywords "AI,자동화,기술"

# 웹 인터페이스 실행
python test_server.py
```

## 🌐 웹 인터페이스

웹 인터페이스를 통해 뉴스레터를 생성하고 이메일로 발송할 수 있습니다:

```bash
python test_server.py
```

브라우저에서 http://localhost:5000 접속

### 웹 인터페이스 기능:
- 🔍 키워드/도메인 기반 뉴스레터 생성
- 📊 실시간 생성 상태 모니터링
- 📧 이메일 발송 및 테스트
- ⏰ **정기 발송 예약**: RRULE 기반 스케줄링
- 📈 **예약 관리**: 활성 스케줄 조회, 취소, 즉시 실행
- 📈 생성 히스토리 관리
- ⚙️ 이메일 설정 상태 확인

### API 엔드포인트

#### Health Check
```bash
GET /health
# 응답: 시스템 상태 및 의존성 확인
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "dependencies": {
    "openai": {"status": "healthy", "latency": 120},
    "serper": {"status": "healthy", "latency": 85},
    "sentry": {"status": "healthy", "config": "enabled"}
  }
}
```

#### 뉴스레터 생성 (API)
```bash
POST /api/generate
{
  "keywords": ["AI", "tech"],
  "period": 7,  # 1, 7, 14, 30일만 허용
  "email": "user@example.com"
}
```

#### 뉴스레터 생성 (GET)
```bash
GET /newsletter?keywords=AI,tech&period=7
# Mock 모드가 비활성화된 경우 실제 뉴스 데이터 반환
# Mock 모드가 활성화된 경우 테스트 데이터 반환
```

#### 정기 발송 예약
```bash
POST /api/schedule
{
  "keywords": ["AI", "tech"],
  "email": "user@example.com",
  "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9"
}
```

#### 예약 관리
```bash
GET /api/schedules              # 활성 예약 목록
DELETE /api/schedule/{id}       # 예약 취소
POST /api/schedule/{id}/run     # 즉시 실행
```

## 📧 이메일 발송 문제 해결

### 문제: "이메일 설정이 완료되지 않았습니다"

**해결방법:**

1. **환경변수 확인:**
   ```bash
   # 환경변수가 제대로 설정되었는지 확인
   python -c "import os; print('POSTMARK_SERVER_TOKEN:', bool(os.getenv('POSTMARK_SERVER_TOKEN'))); print('EMAIL_SENDER:', bool(os.getenv('EMAIL_SENDER')))"
   ```

2. **Postmark 설정 확인:**
   - Postmark 대시보드에서 토큰이 유효한지 확인
   - Signatures에서 발송자 이메일이 인증되었는지 확인
   - 월 발송 한도를 초과하지 않았는지 확인

3. **환경변수 재설정:**
   ```bash
   python setup_env.py
   ```

4. **테스트 이메일 발송:**
   ```bash
   python -m newsletter test-email --to your@email.com
   ```

### 문제: "이메일 모듈을 찾을 수 없습니다"

**해결방법:**

1. **web 디렉토리에서 실행:**
   ```bash
   cd web
   python app.py
   ```

2. **또는 프로젝트 루트에서 실행:**
   ```bash
   python test_server.py
   ```

### 문제: Postmark 오류 코드별 해결방법

- **오류 406 (비활성화된 이메일):**
  - 다른 이메일 주소로 테스트
  - Postmark Suppressions에서 이메일 재활성화

- **오류 300 (잘못된 발송자):**
  - EMAIL_SENDER가 Postmark에서 인증된 이메일인지 확인
  - Signatures에서 발송자 서명 인증

- **오류 401 (인증 실패):**
  - POSTMARK_SERVER_TOKEN이 올바른지 확인
  - Server Token인지 확인 (Account Token 아님)

## 💡 사용 팁

1. **환경변수 우선순위:**
   - `.env` 파일의 설정이 우선 적용됩니다
   - `config.yml`은 LLM 모델 설정에만 사용됩니다

2. **이메일 발송:**
   - CLI와 웹 인터페이스 모두 동일한 환경변수를 사용합니다
   - `EMAIL_SENDER`와 `POSTMARK_FROM_EMAIL`은 동일하게 설정하세요

3. **API 키 관리:**
   - `.env` 파일을 `.gitignore`에 추가하여 버전 관리에서 제외하세요
   - API 키는 절대 공개 저장소에 커밋하지 마세요

## 🔧 개발자 정보

자세한 기술 문서는 `docs/` 디렉토리를 참고하세요.

- [설치 가이드](docs/setup/INSTALLATION.md)
- [CLI 레퍼런스](docs/user/CLI_REFERENCE.md)
- [아키텍처](docs/ARCHITECTURE.md)

## 🧪 테스트

### 자동 테스트 실행

```bash
# 전체 테스트 실행
pytest

# 웹 API 통합 테스트
pytest tests/test_api.py -v

# Mock 모드 및 Period 검증 테스트
pytest tests/test_api.py::test_newsletter_get_endpoint -v
pytest tests/test_api.py::test_period_validation -v

# Health Check 엔드포인트 테스트
pytest tests/test_api.py::test_health_endpoint -v

# Email-Compatible 기능 테스트
pytest tests/test_email_compatibility.py -v

# 통합 테스트 (네트워크 연결 필요)
pytest tests/test_email_compatibility_integration.py -v

# 특정 기능 테스트
pytest tests/test_compose.py::test_email_compatible_rendering -v
```

### 코드 품질 검사

```bash
# Pre-commit hooks 설치
pre-commit install

# 모든 파일에 대해 코드 품질 검사 실행
pre-commit run --all-files

# 개별 도구 실행
black --check newsletter tests
isort --check-only --profile black newsletter tests
flake8 newsletter tests --max-line-length=88 --ignore=E203,W503
```

## 📚 문서

### 사용자 문서
- **[📖 사용자 가이드](docs/user/USER_GUIDE.md)** - 상세한 사용법 및 워크플로우
- **[⚡ CLI 참조](docs/user/CLI_REFERENCE.md)** - 모든 명령어 및 옵션
- **[🔧 설치 가이드](docs/setup/INSTALLATION.md)** - 상세한 설치 및 설정 방법

### 기술 문서
- **[🤖 LLM 설정 가이드](docs/technical/LLM_CONFIGURATION.md)** - 다양한 LLM 제공자 설정 및 최적화
- **[👨‍💻 개발자 가이드](docs/dev/DEVELOPMENT_GUIDE.md)** - 개발 환경 설정 및 기여 방법
- **[🏗️ 시스템 아키텍처](docs/ARCHITECTURE.md)** - 전체 시스템 구조 및 설계
- **[📋 프로젝트 요구사항](docs/PRD.md)** - 프로젝트 목표 및 요구사항

### 프로젝트 정보
- **[📄 변경사항](docs/CHANGELOG.md)** - 버전별 업데이트 내역
- **[📁 전체 문서 목록](docs/README.md)** - 모든 문서의 체계적 안내

## 🤝 기여하기

1. [개발자 가이드](docs/dev/DEVELOPMENT_GUIDE.md)를 읽어보세요
2. 이슈를 생성하거나 기존 이슈를 확인하세요
3. Fork 후 feature branch를 생성하세요
4. 변경사항을 커밋하고 Pull Request를 생성하세요

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 지원

- **[이슈 트래커](https://github.com/hjjung-katech/newsletter-generator/issues)** - 버그 리포트 및 기능 요청
- **[토론](https://github.com/hjjung-katech/newsletter-generator/discussions)** - 질문 및 아이디어 공유
- **[문서](docs/README.md)** - 상세한 사용법 및 개발 가이드

## 🚨 문제 해결

### API 할당량 초과 문제

Google Gemini API의 일일 할당량을 초과한 경우 다음과 같이 해결할 수 있습니다:

#### 1. 현재 LLM 상태 확인
```bash
newsletter check-llm
```

#### 2. 다른 LLM 제공자 사용
OpenAI 또는 Anthropic API 키를 `.env` 파일에 추가:

```bash
# .env 파일에 추가
OPENAI_API_KEY=your_openai_api_key_here
# 또는
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

#### 3. LLM 설정 변경
`config.yml` 파일에서 기본 제공자를 변경:

```yaml
llm_settings:
  default_provider: "openai"  # 또는 "anthropic"
```

#### 4. LLM 테스트
```bash
newsletter test-llm --task keyword_generation --prompt "자율주행 관련 키워드 5개 생성"
```

### 새로운 다중 LLM 기능

이제 여러 LLM 제공자를 동시에 사용할 수 있습니다:

- **Gemini**: 한국어 지원 우수, 빠른 응답
- **OpenAI GPT-4**: 안정적이고 정확한 응답
- **Anthropic Claude**: 자연스러운 글쓰기, 구조화된 작업에 강함

#### 자동 Fallback 기능
- API 할당량 초과 시 자동으로 다른 제공자로 전환
- 429 에러 감지 및 자동 복구
- 사용자 개입 없이 안정적인 서비스 제공

#### 작업별 최적화
각 작업에 가장 적합한 LLM이 자동으로 선택됩니다:
- 키워드 생성: 창의성이 중요한 작업
- 뉴스 요약: 정확성이 중요한 작업  
- HTML 생성: 구조화된 작업
