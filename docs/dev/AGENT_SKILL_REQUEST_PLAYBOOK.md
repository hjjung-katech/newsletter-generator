# Agent/Skill Request Playbook

이 문서는 리포 구조 개선 작업을 `commit + PR + CI` 중심으로 운영하기 위한 요청 표준입니다.

## 목적

- 작업 단위를 PR 중심으로 관리합니다.
- CI 실패/리뷰 코멘트 대응을 스킬로 분리합니다.
- 요청 문장을 표준화해 장기 작업의 재현성을 높입니다.

## 기본 실행 계약

아래 6가지는 기본 요구사항으로 요청에 포함합니다.

1. 브랜치: `codex/<topic>`
2. 커밋: 의미 단위로 분리, 커밋 메시지는 목적 중심
3. 로컬 게이트: `make check`, `make check-full`, 필요 시 `make repo-audit`
4. PR: 변경 요약, 테스트 증빙, 리스크/롤백 포함
5. CI: GitHub Actions 결과 확인 후 상태 보고
6. 실패 처리: 원인 분류 후 수정 커밋 추가, force-push 지양

## Skill 선택 기준

| 상황 | 권장 Skill/Agent | 사용 방식 |
|---|---|---|
| PR의 GitHub Actions 체크 실패 분석/수정 | `$gh-fix-ci` | 실패 로그 수집 -> 원인 요약 -> 수정안 승인 후 반영 |
| 열린 PR의 리뷰 코멘트 반영 | `$gh-address-comments` | 코멘트 수집 -> 선택 항목 확정 -> 순차 반영 |
| 구조 정책/정리 작업 실행 | Repo Hygiene Agent (A) | `repo_audit` + 정책 문서 + small-batch PR |
| 문서 정합성/SSOT 정리 | Docs SSOT Agent (C) | `docs/README.md` 정본 링크 + 링크/스타일 검사 |

## 요청 템플릿 (복사해서 사용)

### 1) 구조 개선 작업 요청

```text
이번 작업은 PR 단위로 진행해줘.
- 목표: <목표>
- 범위: <in-scope / out-of-scope>
- 브랜치: codex/<topic>
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
