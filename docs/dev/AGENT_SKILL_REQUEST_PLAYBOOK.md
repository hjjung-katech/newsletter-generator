# Agent/Skill Request Playbook

이 문서는 작업 단위를 `RR -> Branch -> Commit -> PR -> CI -> Merge`로 고정하기 위한 실행 표준입니다.

## 목적

- 작업 단위를 PR 중심으로 관리합니다.
- CI 실패/리뷰 코멘트 대응을 스킬로 분리합니다.
- 요청 문장을 표준화해 장기 작업의 재현성을 높입니다.

## 기본 실행 계약

아래 9가지는 기본 요구사항으로 요청에 포함합니다.

1. RR(Review Request) 먼저 작성: `.github/ISSUE_TEMPLATE/review-request.yml`
2. RR에는 `Delivery Unit ID`를 필수 기입하고, RR당 PR은 1개만 연동
3. 브랜치: `<type>/<scope>-<topic>` (예: `codex/workflow-template-standard`)
4. 커밋: `.gitmessage.txt` 템플릿 기반으로 의미 단위 분리
5. 커밋 수: 기본 2~6개(예외 라벨: `docs-only`, `trivial`, `hotfix`)
6. 로컬 게이트: `make check`, `make check-full`, 필요 시 `make repo-audit`
7. PR: `.github/pull_request_template.md`에 `## Delivery Unit` 섹션 포함 필수
8. CI: GitHub Actions 결과 확인 후 상태 보고
9. 실패 처리: 원인 분류 후 수정 커밋 추가, force-push 지양

## 자동 적용/강제 원칙

- Codex/Agent는 저장소 루트 `AGENTS.md` 지시를 우선 준수합니다.
- 사람 기여자까지 동일 정책을 적용하기 위해 CI 정책 체크를 함께 사용합니다.
- CI 강제 체크: `.github/workflows/pr-policy-check.yml`
- Delivery Unit 검증 스크립트: `scripts/ci/validate_delivery_unit.py`
- 머지 후 RR 자동 종료: `.github/workflows/rr-lifecycle-close.yml` (`RR: #<n>` 파싱)

## 표준 템플릿 위치

- RR 템플릿: `.github/ISSUE_TEMPLATE/review-request.yml`
- 커밋 템플릿: `.gitmessage.txt`
- PR 템플릿: `.github/pull_request_template.md`
- 종합 문서: `docs/dev/WORKFLOW_TEMPLATES.md`
- Delivery Unit check: `scripts/ci/validate_delivery_unit.py`

로컬 커밋 템플릿 1회 설정:

```bash
git config commit.template .gitmessage.txt
```

## Skill 선택 기준

| 상황 | 권장 Skill/Agent | 사용 방식 |
|---|---|---|
| PR의 GitHub Actions 체크 실패 분석/수정 | `$gh-fix-ci` | 실패 로그 수집 -> 원인 요약 -> 수정안 승인 후 반영 |
| 열린 PR의 리뷰 코멘트 반영 | `$gh-address-comments` | 코멘트 수집 -> 선택 항목 확정 -> 순차 반영 |
| 구조 정책/정리 작업 실행 | Repo Hygiene Agent (A) | `repo_audit` + 정책 문서 + small-batch PR |
| 문서 정합성/SSOT 정리 | Docs SSOT Agent (C) | 정본 우선 갱신 + 링크/스타일 검사 |
| 운영 안전 항목 병행 | Ops Safety Agent (B) | idempotency/outbox/설정 회귀 방지 체크 |
| 릴리즈 전 통합 점검 | Release Guard Agent (D) | preflight + manifest + release template 점검 |

## 요청 템플릿 (복사해서 사용)

### 1) 구조 개선 작업 요청

```text
이번 작업은 PR 단위로 진행해줘.
- 목표: <목표>
- 범위: <in-scope / out-of-scope>
- 브랜치: <type>/<scope>-<topic>
- 필수 게이트: make check, make check-full, make repo-audit
- 산출물: 커밋 해시, PR 링크, CI 상태, 롤백 메모
- 작업 방식: small-batch (PR당 300 LOC, 8 files 내 권장)
```

### 2) CI 실패 대응 요청

```text
$gh-fix-ci를 사용해서 현재 PR의 실패 체크를 분석해줘.
원인 요약과 수정 계획을 먼저 제시하고, 승인 후 코드 수정까지 진행해줘.
```

### 3) 리뷰 코멘트 반영 요청

```text
$gh-address-comments를 사용해서 현재 브랜치 PR 코멘트를 수집해줘.
반영할 항목 번호를 정리해준 뒤 선택한 항목만 수정해줘.
```

## PR 완료 보고 형식

작업 완료 시 아래 형식으로 보고합니다.

1. 커밋 목록(해시 + 요약)
2. PR 링크
3. 로컬 검증 결과(`make check`, `make check-full`, 기타)
4. GitHub Actions 상태(성공/실패, 실패 시 원인)
5. 리스크/롤백 메모
