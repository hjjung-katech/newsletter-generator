# Web API Reference

이 문서는 Flask Web API 계약의 정본(SSOT)입니다.

Base URL (local): `http://localhost:5000`

## Stable Public Endpoints

### `GET /health`
서비스 상태/의존성 상태를 반환합니다.

- `200`: healthy/degraded
- `503`: error

### `POST /api/generate`
비동기 뉴스레터 생성 작업을 등록합니다.

요청 헤더:
- `Idempotency-Key`: `string` (선택, 같은 논리 요청 재시도 시 동일 키 사용 권장)

요청(JSON):
- `keywords`: `string | string[]` (keywords/domain 중 하나 필수)
- `domain`: `string`
- `template_style`: `compact | detailed | modern` (기본 `compact`)
- `email_compatible`: `boolean` (기본 `false`)
- `period`: `1 | 7 | 14 | 30` (기본 `14`)
- `email`: `string` (선택, 있으면 즉시 발송 시도)

응답:
- `202`:
  - 신규 enqueue: `{ "job_id": "...", "status": "queued|processing", "deduplicated": false, "idempotency_key": "..." }`
  - 중복 요청: `{ "job_id": "...", "status": "queued|processing", "deduplicated": true, "idempotency_key": "..." }`
- `400`: 입력 검증 오류

중복 요청 정책:
- 동일한 `Idempotency-Key`(또는 서버가 계산한 canonical payload 키) 재요청은 항상 `202`를 반환합니다.
- 중복 요청 시 기존 `job_id`를 재사용하고 `deduplicated=true`를 반환합니다.

### `GET /api/status/<job_id>`
작업 상태 조회.

응답(JSON):
- `job_id`, `status`, `sent`, `idempotency_key`
- 완료 시 `result`
- 실패 시 `error`

### `GET /api/history`
최근 작업 이력(최대 20개) 조회.

### `POST /api/suggest`
도메인 기반 키워드 추천.

요청(JSON):
- `domain`: `string` (필수)

응답(JSON):
- `keywords`: `string[]`

### `POST /api/schedule`
정기 발송 스케줄 생성.

요청(JSON):
- `rrule`: `string` (필수)
- `email`: `string` (필수)
- `keywords` 또는 `domain` (필수)
- `template_style`, `email_compatible`, `period` (선택)

응답:
- `201`: `{ "status": "scheduled", "schedule_id": "...", "next_run": "..." }`

### `GET /api/schedules`
활성 스케줄 목록 조회.

### `DELETE /api/schedule/<schedule_id>`
스케줄 비활성화(취소).

### `POST /api/schedule/<schedule_id>/run`
스케줄 즉시 실행.

### `GET /api/newsletter-html/<job_id>`
완료된 작업의 HTML 본문 직접 반환 (`text/html`).

### `GET /api/email-config`
이메일 설정 상태 확인.

### `POST /api/send-email`
기 생성된 작업 결과를 지정 이메일로 발송.

요청(JSON):
- `job_id`: `string`
- `email`: `string`

응답(JSON):
- `status`: `success|error`
- `deduplicated`: `boolean` (이미 발송된 동일 요청이면 `true`)
- `send_key`: `string`

### `POST /api/test-email`
테스트 이메일 발송.

요청(JSON):
- `email`: `string`

## Legacy/Debug Endpoints

다음 엔드포인트는 디버그/운영보조 성격이며 외부 공개 API 계약에서 제외합니다.
- `/newsletter`
- `/debug/*`
- `/test*`, `/manual-test`
