# Reviewer Role Setup (Code Owner / Ops Owner)

## 목적

- 릴리즈 PR에서 `code_owner`, `ops_owner` 책임자를 일관되게 적용한다.
- 협업자 수가 부족한 저장소(예: 1인 유지보수)에서도 운영 규칙을 유지한다.

## 기본 설정 파일

경로: `.release/reviewer_roles.json`

예시:

```json
{
  "code_owner": "hjjung-katech",
  "ops_owner": "virtual:ops-owner"
}
```

규칙:
- `code_owner`: 실제 GitHub handle 권장
- `ops_owner`:
  - 실제 handle이 있으면 실제 handle 사용
  - 없으면 `virtual:*` 형식 허용 (예: `virtual:ops-owner`)

## 적용 명령

```bash
make apply-pr-metadata PR=<number>
```

- `REVIEWERS`를 전달하면 역할 파일보다 우선한다.

```bash
make apply-pr-metadata PR=<number> REVIEWERS=<owner1,ops1>
```

## 단일 관리자 저장소(1인 운영) 권장안

1. `code_owner`는 실제 본인 계정으로 둔다.
2. `ops_owner`는 `virtual:ops-owner`로 둔다.
3. PR 템플릿 `PR Metadata Applied`에 Solo/virtual 사용 여부와 근거를 기록한다.

이 방식은 "실제 리뷰 요청"이 기술적으로 불가한 경우에도 운영 책임 분리를 문서로 유지하기 위한 타협안이다.
