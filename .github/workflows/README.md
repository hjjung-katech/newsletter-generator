# GitHub Actions Workflows

이 디렉터리의 canonical 워크플로우는 아래 5개입니다.

## Active Workflows (Canonical)

1. `main-ci.yml`
- 목적: 코드 품질, 테스트, 빌드 검증의 메인 CI 파이프라인
- 트리거: `push`(main/develop/feature/fix), `pull_request`(main/develop)

2. `deployment.yml`
- 목적: 배포 파이프라인 (Railway + Pages 병행)
- 트리거: `push`(main), `schedule`, `workflow_dispatch`

3. `security-scan.yml`
- 목적: 정기 보안 스캔
- 트리거: `schedule`, `workflow_dispatch`

4. `docs-quality.yml`
- 목적: 문서 링크/스타일 품질 검증
- 트리거: markdown 변경 `pull_request`/`push`

5. `ops-safety-monitor.yml`
- 목적: 운영 안전성 점검 모니터링
- 트리거: `schedule`, `workflow_dispatch`

## Policy

- 위 5개만 운영 워크플로우로 유지합니다.
- 중복/레거시 워크플로우 파일은 저장소에 두지 않습니다.
- 변경 시 이 문서와 실제 파일 목록을 항상 1:1로 맞춥니다.

## Quick Check

```bash
ls .github/workflows
```

출력은 다음 파일만 포함해야 합니다.

- `README.md`
- `main-ci.yml`
- `deployment.yml`
- `security-scan.yml`
- `docs-quality.yml`
- `ops-safety-monitor.yml`
