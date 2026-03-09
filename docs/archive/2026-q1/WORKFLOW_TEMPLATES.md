# Workflow Templates (RR / Branch / Commit / PR)

> Historical note (2026-03-09): RR-07에서 active docs tree 밖으로 이관된 문서입니다.
> 현재 contributor workflow 정본은 `docs/dev/CI_CD_GUIDE.md` 입니다.

이 문서는 작업 요청(RR)부터 브랜치/커밋/PR/머지까지 하나의 운영 표준으로 맞추기 위한 템플릿 모음입니다.

## 1) RR(Review Request) 템플릿

> RR = 구현 착수 전에 범위/리스크/검증 계획을 잠그는 요청서.

```md
# RR: <작업 제목>

## Goal
- 왜 지금 이 작업이 필요한가?

## In Scope
- 항목 1
- 항목 2

## Out of Scope
- 이번 PR에서 하지 않을 것

## Impact / Risk
- 영향 받는 모듈:
- 운영 리스크:
- 롤백 방법:

## Validation Plan
- [ ] make check
- [ ] make check-full
- [ ] 추가 테스트: <command>

## Delivery Unit
- Branch: <type>/<scope>-<topic>
- Delivery Unit ID: DU-YYYYMMDD-<topic>
- Expected PR size: <= 300 LOC, <= 8 files
```

## 2) 브랜치 네이밍 템플릿

- 기본 패턴: `<type>/<scope>-<short-topic>`
- type 허용값: `feat`, `fix`, `chore`, `docs`, `refactor`, `release`, `codex`

예시:
- `feat/web-idempotency-key`
- `fix/scheduler-duplicate-send`
- `docs/pr-policy-unification`
- `codex/workflow-template-standard`

## 3) 커밋 메시지 템플릿

- 기본 패턴: `<type>(<scope>): <summary>`
- summary는 72자 이내, 명령형, why 중심.
- 기본 커밋 수: PR당 1~6개
- 예외 라벨: `docs-only`, `trivial`, `hotfix`

예시:
- `docs(workflow): add RR/branch/commit/PR standard templates`
- `fix(web): reuse idempotent job for duplicate generation requests`

멀티 커밋 PR 권장 순서:
1. contract/test lock
2. implementation
3. docs/policy sync

## 4) PR 템플릿 운영 규칙

PR 본문은 아래 7개 섹션을 고정합니다.

1. Summary (what/why)
2. Scope (in/out)
3. Delivery Unit (`RR: #<n>`, `Delivery Unit ID`, Merge/Rollback Boundary)
4. Test & Evidence (명령어 + 결과)
5. Risk & Rollback
6. Ops-Safety Addendum (해당 시)
7. Not Run (미실행 항목 + 사유)

## 5) 머지 정책(권장 기본값)

- Merge 방식: **Squash merge** 기본
- Merge 조건:
  - 필수 체크 성공 (`make check-full`와 CI)
  - PR 템플릿 필수 섹션 누락 없음
  - 리뷰는 기본 비필수, 필요 시 고위험 변경에만 요청
- Merge 후 자동 처리:
  - `.github/workflows/rr-lifecycle-close.yml`가 `RR: #<n>`를 읽어 RR 이슈를 자동 close
- 금지:
  - force-push로 리뷰 이력 소거
  - 테스트 증빙 없는 긴급 머지(사후 보완 없는 경우)

## 6) 저장소 반영 위치

- RR 템플릿: `.github/ISSUE_TEMPLATE/review-request.yml`
- PR 템플릿: `.github/pull_request_template.md`
- 커밋 템플릿: `.gitmessage.txt`
- 에이전트 실행 가이드: `docs/dev/AGENT_SKILL_REQUEST_PLAYBOOK.md`

## 7) 적용 명령

```bash
git config commit.template .gitmessage.txt
```

로컬 1회 설정 후 모든 커밋에서 템플릿이 자동 로드됩니다.

## 8) "별도 지시 없이도 Codex가 따르는가?" 적용 범위

- **Codex/Agent 작업:** 저장소 루트 `AGENTS.md` 스코프 내 작업에서는 기본적으로 본 정책을 따릅니다.
- **사람 기여자 작업:** 템플릿만으로는 강제가 약하므로, CI 체크/브랜치 보호 규칙과 함께 운영해야 실효성이 생깁니다.
- **예외 처리:** hotfix 등 예외 머지는 PR 본문 `Not Run`에 근거를 남기고, 후속 보완 PR을 명시합니다.

## 9) 강제 수단(권장 -> 적용)

- 적용됨: `.github/workflows/pr-policy-check.yml`
  - 브랜치명 패턴 검사
  - PR 본문 필수 섹션 존재 검사
  - 커밋 메시지 패턴 검사
  - Delivery Unit 정책 검사(`scripts/ci/validate_delivery_unit.py`)
- 추가 권장(GitHub 설정):
  - Branch protection에서 `PR Policy Check`를 required check로 지정
  - Squash merge만 허용
  - 기본 approval required 없음 (`required_approving_review_count=0`)

## 10) 커밋 메시지 세부 가이드 (누락 보완)

- 헤더 형식: `<type>(<scope>): <summary>`
- `type` 허용값: `feat|fix|chore|docs|refactor|release|codex`
- `scope`는 소문자/숫자/`._-`만 허용(선택)
- summary 규칙:
  - 첫 글자 소문자 권장, 명령형
  - 72자 이하
  - 마침표(`.`)로 끝내지 않음
- 본문(선택)에는 Why/What/Validation/Risk를 작성

유효 예시:
- `fix(web): prevent duplicate email sends with send_key guard`
- `docs(policy): define mandatory commit message conventions`

비유효 예시:
- `Update code`
- `hotfix:stuff`
- `Fix(Web): This is too long ...`

CI(`PR Policy Check`)에서 PR 내 커밋의 첫 줄을 위 규칙으로 검사합니다.
