# Lessons Learned

## RR-26 policy-check 위반 패턴 (2026-04-13)

### 위반 1: 브랜치명 타입 오류
- **무엇이 틀렸나**: `ops-security/rr-26-scoped-token-auth` — `ops-security`는 허용 타입이 아님
- **규칙**: CI regex `^(feat|fix|chore|docs|refactor|release|codex)\/[a-z0-9._-]+$`
- **교훈**: 브랜치 생성 전 타입이 `feat|fix|chore|docs|refactor|release|codex` 중 하나인지 확인

### 위반 2: PR 섹션 타이틀 불일치
- **무엇이 틀렸나**: `## Ops-Safety Addendum` → 정확한 타이틀은 `## Ops-Safety Addendum (if touching protected paths)`
- **교훈**: PR 본문 섹션 타이틀은 `.github/pull_request_template.md`와 완전 일치해야 함

### 위반 3: RR 번호 형식 오류
- **무엇이 틀렸나**: `RR: #209 (RR-26)` → 괄호 표기 불가
- **규칙**: 정확히 `RR: #<number>` 형식만 허용
- **교훈**: RR 번호 뒤에 어떤 텍스트도 추가하지 말 것

### 위반 4: Issue에 review-request 레이블 없음
- **무엇이 틀렸나**: Issue #209에 `review-request` 레이블이 없어서 governance 검사 실패
- **교훈**: PR 생성 전 참조 Issue에 `review-request` 레이블 확인 및 추가

### 위반 5: Delivery Unit ID 형식
- **CLAUDE.md 명세**: `DU-YYYYMMDD-<topic>` 형식
- **교훈**: `Delivery Unit ID: DU-20260413-redis-rate-limiting` 형식 사용

## PR 생성 전 필수 체크리스트

```
[ ] 브랜치명: feat|fix|chore|docs|refactor|release|codex 로 시작, 소문자+숫자+점+대시만 허용
[ ] PR 섹션: ## Ops-Safety Addendum (if touching protected paths) 정확히 일치
[ ] RR 형식: RR: #<number> (괄호/추가텍스트 금지)
[ ] Issue에 review-request 레이블 확인 → 없으면 추가
[ ] Delivery Unit ID: DU-YYYYMMDD-<topic> 형식
```
