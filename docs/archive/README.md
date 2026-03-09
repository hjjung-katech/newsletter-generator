# Archive Policy

`docs/archive/` 는 운영 정본에서 분리한 이력성 문서를 보관하는 공간입니다.
문서 삭제는 즉시 수행하지 않고, 먼저 archive 버킷으로 이동한 뒤 한 릴리즈 주기 동안 유지합니다.

## Bucket Naming

- 버킷 이름은 `YYYY-qN` 형식을 사용합니다.
- 월 단위 임시 버킷이 있으면 다음 정리 배치에서 분기 버킷으로 정규화합니다.

## Current Buckets

- [`2026-q1/README.md`](2026-q1/README.md)
- [`webservice-prd.md`](webservice-prd.md)

## Rollback

archive 된 문서를 active tree 로 복원해야 하면 원래 경로로 되돌린 뒤,
[`../DOCUMENT_INVENTORY.md`](../DOCUMENT_INVENTORY.md) 와 관련 허브 링크를 함께 원복합니다.
