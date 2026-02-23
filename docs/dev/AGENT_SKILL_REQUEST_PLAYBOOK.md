# Agent/Skill Request Playbook

이 문서는 작업 단위를 `request(RR) -> commit -> PR -> CI -> merge`로 고정하기 위한 실행 표준입니다.

## 목적

- 모든 작업을 PR 단위로 완료합니다.
- Agent/Skill을 단계별로 명확히 연결합니다.
- 템플릿 기반으로 커밋/PR/브랜치 품질을 일관되게 유지합니다.

## One-Unit Process (Definition of Done)

하나의 업무 단위는 아래 7단계를 모두 충족해야 종료합니다.

1. 요청(RR) 범위 확정
2. 브랜치 생성(`codex/<topic>`)
3. 커밋(템플릿 기반)
4. PR 생성(템플릿 기반)
5. 로컬 게이트 통과(`make check`, `make check-full`, 필요 시 `make repo-audit`)
6. PR CI 통과 후 merge
7. merge 이후 `main` 기준 CI 상태 확인

## Template SSOT

- RR/작업 요청 템플릿: `docs/dev/RR_REQUEST_TEMPLATE.md`
- PR 템플릿(기본): `.github/pull_request_template.md`
- PR 템플릿(특화): `.github/PULL_REQUEST_TEMPLATE/repo_hygiene.md`, `.github/PULL_REQUEST_TEMPLATE/release_integration.md`
- Commit 템플릿: `.github/COMMIT_TEMPLATE.txt`
- 로컬 Git 템플릿 설정 스크립트: `scripts/devtools/setup_git_message_template.sh`

## Branch Naming Policy

- 형식: `<type>/<kebab-case-topic>`
- 권장 타입: `codex`, `feature`, `fix`, `bugfix`, `hotfix`, `chore`, `docs`, `refactor`, `test`, `release`
- 예시:
  - `codex/week3-root-slimming`
  - `fix/ci-process-contract`

`main-ci.yml`에서 PR 시 브랜치명/PR 본문 템플릿 섹션을 검증합니다.

## Skill/Agent 연결 규칙

| 단계 | 권장 Skill/Agent | 사용 방식 |
|---|---|---|
| PR CI 실패 분석/수정 | `$gh-fix-ci` | 실패 로그 수집 -> 원인 요약 -> 승인 후 수정 |
| 리뷰 코멘트 반영 | `$gh-address-comments` | 코멘트 수집 -> 반영 항목 합의 -> 순차 반영 |
| 구조 정책/정리 실행 | Repo Hygiene Agent (A) | `repo_audit` + 정책 문서 + small-batch PR |
| 문서 SSOT/정합성 정리 | Docs SSOT Agent (C) | SSOT 우선 갱신 + 링크/스타일 검사 |
| 운영 안전 항목 병행 | Ops Safety Agent (B) | idempotency/outbox/설정 회귀 방지 체크 |
| 릴리즈 전 통합 점검 | Release Guard Agent (D) | preflight + manifest + release template 점검 |

## 요청 템플릿 (RR)

### 1) 일반 작업 요청

```text
이번 작업은 PR 단위로 끝까지 진행해줘.
- 목표: <목표>
- 범위: <in-scope / out-of-scope>
- 브랜치: codex/<topic>
- 필수 게이트: make check, make check-full
- 선택 게이트: make repo-audit (구조/정책 변경 시)
- 산출물: 커밋 해시, PR 링크, CI 상태, merge 결과, 롤백 메모
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

## 완료 보고 형식

작업 완료 시 아래 형식으로 보고합니다.

1. 커밋 목록(해시 + 요약)
2. PR 링크
3. 로컬 검증 결과(`make check`, `make check-full`, 기타)
4. PR CI 상태 + merge 후 `main` CI 상태
5. 리스크/롤백 메모
