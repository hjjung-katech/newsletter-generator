# Environment Variables Reference

이 문서는 환경변수 계약의 정본(SSOT)입니다.

## Runtime Contract

| 변수 | 필수 여부 | 용도 |
|---|---|---|
| `SERPER_API_KEY` | 생성 기능 필수 | 뉴스 검색 API |
| `GEMINI_API_KEY` | LLM 중 하나 필수 | Gemini 제공자 |
| `OPENAI_API_KEY` | LLM 중 하나 필수 | OpenAI 제공자 |
| `ANTHROPIC_API_KEY` | LLM 중 하나 필수 | Anthropic 제공자 |
| `POSTMARK_SERVER_TOKEN` | 이메일 발송 시 필수 | Postmark 서버 토큰 |
| `EMAIL_SENDER` | 이메일 발송 시 필수 | 발신자 이메일 (인증 필요) |
| `SECRET_KEY` | 프로덕션 권장(웹) | Flask 시크릿 키 |
| `ADMIN_API_TOKEN` | 민감 운영 API 보호 시 필수 | `/api/history`, `/api/schedule*`, `/api/send-email`, `/api/email-config`, `/api/test-email` 보호 토큰 |
| `REDIS_URL` | worker/scheduler 사용 시 필수 | Redis 연결 |
| `RQ_QUEUE` | 선택 | RQ 큐 이름 (`default`) |
| `FLASK_ENV` | 선택 | `development`/`production` |
| `MOCK_MODE` | 선택 | `true`일 때 mock 데이터 사용 |
| `TESTING` | 테스트 전용 | 테스트 모드 강제 |
| `SENTRY_DSN` | 선택 | Sentry 에러 모니터링 |
| `PORT` | 배포 시 선택 | 웹 포트 (기본 `5000`) |

## LLM Key Rule

실제 생성 경로에서는 아래 중 최소 1개 이상이 필요합니다.
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

## Compatibility Alias

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
# 최소 생성(비이메일)
SERPER_API_KEY=...
GEMINI_API_KEY=...

# 이메일 발송 포함
POSTMARK_SERVER_TOKEN=ps_xxx
EMAIL_SENDER=newsletter@example.com

# 웹/운영
SECRET_KEY=replace-me-in-production
ADMIN_API_TOKEN=replace-me-with-an-ops-token
REDIS_URL=redis://localhost:6379/0
```
