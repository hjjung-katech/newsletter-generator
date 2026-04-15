# GitHub Actions Workflows

이 디렉터리의 canonical 워크플로우는 아래 9개입니다.

## Active Workflows (Canonical)

1. `main-ci.yml`
- 목적: 코드 품질, 테스트, 빌드 검증의 메인 CI 파이프라인
- 트리거: `push`(main/develop/release/**), `pull_request`(main/develop)
- 참고: PR 정책 검증은 `pr-policy-check.yml`에서 수행
- 현재 `main` branch protection required checks:
  - `policy-check`, `docs-quality`, `Code Quality & Security`, `Release Preflight`
  - `Unit Tests - ubuntu-latest-py3.11`, `Unit Tests - ubuntu-latest-py3.12`
  - `Source Smoke (ubuntu-latest)`, `Source Smoke (macos-latest)`, `Source Smoke (windows-latest)`
  - `Build Check (ubuntu-latest)`, `Build Check (windows-latest)`, `Container Smoke (ubuntu-latest)`
- 추가 PR validation: `Mock API Tests`

2. `deployment.yml`
- 목적: 배포 파이프라인 (Railway + Pages 병행)
- 트리거: `push`(main), `schedule`, `workflow_dispatch`

3. `security-scan.yml`
- 목적: 정기 보안 스캔
- 트리거: `schedule`, `workflow_dispatch`

4. `docs-quality.yml`
- 목적: 문서 링크/스타일 품질 검증
- 트리거: `main`/`develop` 대상 `pull_request`/`push`
- 동작: required check 가 항상 emit 되며, docs 관련 변경이 없으면 no-op pass 로 종료

5. `ops-safety-monitor.yml`
- 목적: 운영 안전성 점검 모니터링
- 트리거: `schedule`, `workflow_dispatch`

6. `pr-policy-check.yml`
- 목적: PR 브랜치명/템플릿/커밋 메시지 정책 검증
- 트리거: `pull_request` (`opened`, `edited`, `synchronize`, `reopened`)

7. `rr-lifecycle-close.yml`
- 목적: 머지된 PR 본문의 `RR: #<n>`를 기준으로 RR 이슈 자동 종료
- 트리거: `pull_request` (`closed`, merged only)

8. `shell-size-gate.yml`
- 목적: freeze 모듈 5개 LOC/복잡도 측정 — soft-gate(항상 통과), PR comment + Step Summary 출력
- 트리거: `pull_request` (main 대상)

9. `e2e-smoke.yml`
- 목적: 핵심 흐름 2개 (GET /health, GET /) Playwright E2E 스모크 테스트 — blocking CI gate
- 트리거: `pull_request` (main 대상)

## Policy

- 위 9개만 운영 워크플로우로 유지합니다.
- 중복/레거시 워크플로우 파일은 저장소에 두지 않습니다.
- 변경 시 이 문서와 실제 파일 목록을 항상 1:1로 맞춥니다.
- `main-ci.yml`은 PR gate와 long gate를 같이 담지만, contributor-facing canonical command는 `python -m scripts.devtools.dev_entrypoint ...`를 유지합니다.

## CI Flake Retry Policy

- 재시도는 네트워크성 실패(예: `ReadTimeout`, `Connection reset`, `Could not fetch URL`)에만 허용합니다.
- 코드/테스트 실패는 재시도 없이 즉시 실패 처리합니다.
- `main-ci.yml`의 빌드 단계는 위 정책으로 `pip install` 재시도를 제한 적용합니다.

## Windows Release Variables/Secrets

- Secret: `WINDOWS_OV_CERT_SHA1` (OV 코드서명 인증서 thumbprint)
- Secret: `WINDOWS_OV_CERT_PFX_BASE64` (OV 인증서 PFX base64 payload, release 경로 필수)
- Secret: `WINDOWS_OV_CERT_PASSWORD` (PFX password, release 경로 필수)
- Variable: `WINDOWS_UPDATE_BASE_URL` (`update-manifest.json`의 다운로드 base URL)

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
- `pr-policy-check.yml`
- `rr-lifecycle-close.yml`
- `shell-size-gate.yml`
- `e2e-smoke.yml`
