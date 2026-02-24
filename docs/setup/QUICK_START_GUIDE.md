# Newsletter Generator 빠른 시작 (5분)

이 문서는 최소 실행 경로만 제공합니다. 상세 설정은 정본 문서로 이동하세요.

## 1. 저장소 준비

```bash
git clone https://github.com/hjjung-katech/newsletter-generator.git
cd newsletter-generator
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
```

## 2. 의존성 설치

```bash
pip install -r requirements.txt
pip install -r web/requirements.txt
```

## 3. 환경변수 설정

```bash
cp .env.example .env
```

최소 필수값:

```bash
SERPER_API_KEY=...
GEMINI_API_KEY=...  # 또는 OPENAI_API_KEY / ANTHROPIC_API_KEY 중 1개
```

이메일 발송까지 테스트하려면:

```bash
POSTMARK_SERVER_TOKEN=ps_xxx
EMAIL_SENDER=newsletter@example.com
```

## 4. 웹 실행

```bash
cd web
python init_database.py
python app.py
```

브라우저: `http://localhost:5000`
헬스체크: `http://localhost:5000/health`

## 5. 확인 포인트

- Generate 요청이 성공하면 HTML 결과가 표시됩니다.
- 이메일 발송은 `POSTMARK_SERVER_TOKEN` + `EMAIL_SENDER`가 모두 있을 때만 활성 동작합니다.

## 정본 문서

- 설치 상세: `INSTALLATION.md`
- 로컬 개발/Redis/워커: `LOCAL_SETUP.md`
- Railway 배포: `RAILWAY_DEPLOYMENT.md`
- 환경변수 계약(SSOT): `../reference/environment-variables.md`
- 웹 API 계약(SSOT): `../reference/web-api.md`
