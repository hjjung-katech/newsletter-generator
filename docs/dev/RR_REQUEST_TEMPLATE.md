# RR (Request/Review) Template

이 문서는 에이전트 작업 요청(RR)을 표준화하기 위한 템플릿입니다.

## Standard RR

```text
이번 작업은 PR 단위로 끝까지 진행해줘.
- 목표: <목표>
- 범위: <in-scope / out-of-scope>
- 브랜치: codex/<topic>
- 필수 게이트: make check, make check-full
- 선택 게이트: make repo-audit (구조/정책 변경 시)
- 산출물: 커밋 해시, PR 링크, CI 상태, merge 결과, 롤백 메모
```

## RR for CI Failure

```text
$gh-fix-ci를 사용해서 현재 PR의 실패 체크를 분석해줘.
원인 요약과 수정 계획을 먼저 제시하고, 승인 후 코드 수정까지 진행해줘.
```

## RR for Review Comments

```text
$gh-address-comments를 사용해서 현재 브랜치 PR 코멘트를 수집해줘.
반영할 항목 번호를 정리해준 뒤 선택한 항목만 수정해줘.
```
