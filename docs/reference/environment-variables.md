# Environment Variables Reference

이 문서는 환경변수 계약의 정본(SSOT)입니다.

## Sample Files

- 루트 [`../../.env.example`](../../.env.example)는 canonical Flask/CLI runtime 샘플입니다.
- [`../../apps/experimental/.env.example`](../../apps/experimental/.env.example)는
  `apps/experimental/main.py` 전용 FastAPI/security 확장 샘플입니다.
- `HOST`, `PORT`, `ALLOWED_ORIGINS` 는 두 런타임이 공유하지만, root sample을 기준으로 유지합니다.

## Canonical Runtime Contract

### Core Runtime / Web Ops

| 변수 | 필수 여부 | 용도 |
|---|---|---|
| `APP_ENV` | 선택 | canonical runtime environment (`development`/`testing`/`production`) |
| `FLASK_ENV` | 호환용 | legacy web entrypoint dev/prod 토글 |
| `ENVIRONMENT` | 호환용 | legacy logging/security/runtime fallback |
| `DEBUG` | 선택 | 개발 편의용 디버그 플래그 |
| `HOST` | 선택 | 웹 바인딩 호스트 |
| `PORT` | 배포 시 선택 | 웹 포트 (`.env.example` 기준 `8000`, legacy entrypoint는 미설정 시 `5000` fallback 존재) |
| `LOG_LEVEL` | 선택 | runtime/application log level |
| `LOG_FORMAT` | 선택 | logging format (`standard`/`json`) |
| `SECRET_KEY` | 프로덕션 권장(웹) | Flask 시크릿 키 |
| `ADMIN_API_TOKEN` | 민감 운영 API 보호 시 필수 | `/api/history`, `/api/schedule*`, `/api/send-email`, `/api/email-config`, `/api/test-email` 보호 토큰 |
| `ALLOWED_ORIGINS` | 선택 | canonical Flask runtime CORS allow-list |

### Search / LLM / Delivery

| 변수 | 필수 여부 | 용도 |
|---|---|---|
| `SERPER_API_KEY` | 생성 기능 필수 | 뉴스 검색 API |
| `GEMINI_API_KEY` | LLM 중 하나 필수 | Gemini 제공자 |
| `OPENAI_API_KEY` | LLM 중 하나 필수 | OpenAI 제공자 |
| `ANTHROPIC_API_KEY` | LLM 중 하나 필수 | Anthropic 제공자 |
| `POSTMARK_SERVER_TOKEN` | 이메일 발송 시 필수 | Postmark 서버 토큰 |
| `EMAIL_SENDER` | 이메일 발송 시 필수 | 발신자 이메일 (인증 필요) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Drive 저장 시 선택 | GCP 서비스 계정 키 경로 |
| `GOOGLE_CLIENT_ID` | OAuth 사용 시 선택 | Google OAuth client id |
| `GOOGLE_CLIENT_SECRET` | OAuth 사용 시 선택 | Google OAuth client secret |
| `NAVER_CLIENT_ID` | 네이버 API 사용 시 선택 | Naver client id |
| `NAVER_CLIENT_SECRET` | 네이버 API 사용 시 선택 | Naver client secret |

### Optional Integrations / Observability / Test

| 변수 | 필수 여부 | 용도 |
|---|---|---|
| `LANGCHAIN_API_KEY` | LangSmith 사용 시 선택 | LangSmith API key |
| `LANGCHAIN_TRACING_V2` | LangSmith 사용 시 선택 | tracing 토글 |
| `LANGCHAIN_PROJECT` | LangSmith 사용 시 선택 | tracing project name |
| `DATABASE_URL` | DB persistence 사용 시 선택 | 애플리케이션 DB 연결 문자열 |
| `REDIS_URL` | worker/scheduler 사용 시 필수 | Redis 연결 |
| `RQ_QUEUE` | 선택 | RQ 큐 이름 (`default`) |
| `SENTRY_DSN` | 선택 | Sentry 에러 모니터링 |
| `SENTRY_TRACES_SAMPLE_RATE` | 선택 | Sentry tracing sample rate |
| `SENTRY_PROFILES_SAMPLE_RATE` | 선택 | Sentry profiling sample rate |
| `ADDITIONAL_RSS_FEEDS` | 선택 | 추가 RSS feed 목록 |
| `TESTING` | 테스트 전용 | 테스트 모드 강제 |
| `MOCK_MODE` | 선택 | `true`일 때 mock 데이터 사용 |

## Experimental FastAPI / Security Extension

`apps/experimental/main.py` 와 `newsletter.security.*` 계층은 아래 변수를 추가로 사용합니다.
이 값들은 root `.env.example` 에 두지 않고 [`../../apps/experimental/.env.example`](../../apps/experimental/.env.example)
로 분리합니다.

| 변수 | 필수 여부 | 용도 |
|---|---|---|
| `ALLOWED_HOSTS` | 선택 | FastAPI trusted host allow-list |
| `JWT_SECRET_KEY` | 실험 API auth 사용 시 필수 | JWT 서명 키 |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 선택 | JWT access token 만료 시간 |
| `RATE_LIMIT_ENABLED` | 선택 | experimental rate limiting 토글 |
| `RATE_LIMIT_REQUESTS` | 선택 | rate limit 요청 수 |
| `RATE_LIMIT_WINDOW` | 선택 | rate limit 윈도우(초) |
| `MAX_UPLOAD_SIZE` | 선택 | 업로드 파일 최대 크기(byte) |
| `SESSION_COOKIE_SECURE` | 선택 | secure cookie 강제 여부 |
| `LOG_DIR` | 선택 | security/app audit log 디렉터리 |
| `SECURITY_AUDIT_LOG` | 선택 | 보안 감사 로그 파일명 |
| `APPLICATION_LOG` | 선택 | 애플리케이션 로그 파일명 |

## LLM Key Rule

실제 생성 경로에서는 아래 중 최소 1개 이상이 필요합니다.
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

## Compatibility Alias

- `FLASK_ENV`
  - direct `web/app.py` 실행 경로와의 호환용입니다.
  - 신규 로컬/운영 설정에서는 `APP_ENV` 를 우선 사용하고, 필요 시 같은 값으로 함께 설정합니다.
- `ENVIRONMENT`
  - 일부 legacy logging/security 경로의 fallback 입니다.
  - 신규 설정에서는 `APP_ENV` 를 우선 사용하고, 필요 시 같은 값으로 함께 설정합니다.
- `POSTMARK_FROM_EMAIL`
  - 읽기 전용 호환 별칭입니다.
  - 신규 설정/문서에서는 사용하지 않습니다.

## Deprecated (Do Not Use)

다음 변수는 문서/샘플/신규 코드에 사용하지 않습니다.
- `SENDGRID_API_KEY`
- `FROM_EMAIL`
- `POSTMARK_TOKEN`
- `POSTMARK_API_TOKEN`

## Examples

```bash
# canonical Flask/CLI runtime
SERPER_API_KEY=...
GEMINI_API_KEY=...
APP_ENV=development

# 이메일 발송 포함
POSTMARK_SERVER_TOKEN=ps_xxx
EMAIL_SENDER=newsletter@example.com

# 웹/운영
APP_ENV=production
FLASK_ENV=production
ENVIRONMENT=production
SECRET_KEY=replace-me-in-production
ADMIN_API_TOKEN=replace-me-with-an-ops-token
ALLOWED_ORIGINS=https://app.example.com
REDIS_URL=redis://localhost:6379/0

# experimental FastAPI runtime extension
JWT_SECRET_KEY=replace-me-for-experimental-runtime
ALLOWED_HOSTS=api.example.com
RATE_LIMIT_ENABLED=true
```
