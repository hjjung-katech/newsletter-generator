# Project Instructions (newsletter-generator)

## Non-negotiables
- Never commit secrets. Never print real API keys in logs, docs, or PR descriptions.
- Default to MOCK_MODE for local tests and smoke runs unless explicitly testing real APIs.
- Keep Flask + Postmark as the canonical runtime stack for web delivery.
- Keep FastAPI under `apps/experimental/` only (non-canonical runtime path).
- Treat `POSTMARK_SERVER_TOKEN` and `EMAIL_SENDER` as canonical env vars.
- Allow `POSTMARK_FROM_EMAIL` only as a read-only compatibility alias.
- Do not introduce `SENDGRID_API_KEY`, `FROM_EMAIL`, `POSTMARK_TOKEN`, or `POSTMARK_API_TOKEN` into active docs/samples.

## Required Gate After Code Changes
- Run: `make check-full`
- If full run is too expensive during iteration, run: `make check` first and then `make check-full` before completion.

## PR Size Policy
- Keep each PR within 300 LOC and 8 files whenever possible.
- For large refactors, lock contract tests first and split into sequential PRs.

## Repo Truth Sources
- CI gate: `run_ci_checks.py`
- Release preflight: `scripts/release_preflight.py`
- Manifest validator: `scripts/validate_release_manifest.py`
- Release manifests: `.release/manifests/*.txt`

## Required Report Format For Changes
- Short summary: what changed and why
- Exact commands executed
- Pass/fail evidence from checks/tests
- What was not run and why

## High-Risk Areas (extra caution)
- `web/app.py`, `web/tasks.py`, `web/schedule_runner.py`
- `newsletter/centralized_settings.py`, `newsletter/config_manager.py`
- Release gate scripts and Makefile targets

## Operational Safety First (Priority Override)
- 운영 안전성 잠금이 경계 리팩토링보다 우선입니다.
- 아래 두 축이 잠기기 전까지 구조 리팩토링은 제한적으로 수행합니다:
  - 설정 단일화 (`newsletter/centralized_settings.py` 중심)
  - 스케줄/워커 idempotency + 이메일 중복 방지(outbox)

## Config Unification Policy (Mandatory)
- 설정 읽기/검증/기본값 책임은 `newsletter/centralized_settings.py`를 단일 소스로 유지합니다.
- `newsletter/config_manager.py`는 호환용 thin adapter 역할만 유지합니다.
- import-time side effect를 금지합니다 (`load_dotenv()`를 모듈 import 시 실행 금지).
- 프로덕션 경로 기본값은 production-safe여야 합니다 (`test_mode=False` 기본).
- canonical env는 `POSTMARK_SERVER_TOKEN`, `EMAIL_SENDER`이며,
  `POSTMARK_FROM_EMAIL`은 read-only compatibility alias만 허용합니다.

## Idempotency Policy (Mandatory)
- 생성 요청은 `Idempotency-Key` 헤더 우선 정책을 따릅니다.
- 헤더가 없으면 canonical payload hash로 idempotency key를 생성합니다.
- 동일 logical request는 동일 idempotency key를 사용하고 기존 job을 재사용합니다.
- 중복 요청 응답은 항상 `202`이며 `deduplicated=true`를 포함해야 합니다.
- 이메일 발송은 outbox/send_key 기반으로 중복 발송을 차단해야 합니다.
- sync/async/fallback 경로는 공통 DB 상태전이 함수를 사용해야 합니다.

## Required Gate For Ops-Safety Changes
- 대상 파일:
  - `newsletter/centralized_settings.py`, `newsletter/config_manager.py`
  - `web/app.py`, `web/tasks.py`, `web/schedule_runner.py`, `web/routes_generation.py`, `web/routes_send_email.py`
- 필수 실행:
  - `make check`
  - `make check-full`
  - `pytest tests/test_web_api.py -q`
  - `pytest tests/integration/test_schedule_execution.py -q`
  - `pytest tests/unit_tests/test_schedule_time_sync.py -q`

## PR Report Addendum (Ops-Safety)
- idempotency key 생성/적용 범위를 명시합니다.
- outbox/send_key 기반 이메일 중복 방지 결과를 명시합니다.
- import-time side effect 제거 여부를 명시합니다.
- 미실행 테스트와 사유를 반드시 기록합니다.

## Workflow Standardization (RR/Branch/Commit/PR)
- 모든 작업은 RR(Review Request) -> Branch -> Commit -> PR -> Merge 순서를 기본 프로세스로 따릅니다.
- RR은 `.github/ISSUE_TEMPLATE/review-request.yml` 템플릿을 사용합니다.
- 브랜치명은 `<type>/<scope>-<topic>` 패턴을 사용합니다.
- 커밋 메시지는 `.gitmessage.txt` 템플릿을 기준으로 작성합니다.
- PR 본문은 `.github/pull_request_template.md` 섹션을 누락 없이 채웁니다.
- RR과 PR은 1:1 Delivery Unit 경계를 유지합니다 (`RR: #<n>`, `Delivery Unit ID` 필수).
- 하나의 RR(또는 Delivery Unit ID)을 동시에 여러 open PR에서 재사용하면 안 됩니다.
- 기본 커밋 수는 PR당 2~6개를 권장/강제합니다 (예외 라벨: `docs-only`, `trivial`, `hotfix`).
- 기본 머지 전략은 squash merge이며, 증빙 없는 예외 머지는 금지합니다.
- CI에서 `.github/workflows/pr-policy-check.yml`로 브랜치/PR 템플릿 + 커밋 메시지 규칙을 검증합니다.
- 머지 완료 후 `.github/workflows/rr-lifecycle-close.yml`가 PR 본문의 `RR: #<n>`을 기준으로 RR 이슈를 자동 종료합니다.
