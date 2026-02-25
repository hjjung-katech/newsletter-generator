# Windows EXE 운영 정책

작성일: 2026-02-24

## 1) 코드서명 정책 (OV)

- 목표: GA(정식 배포) 경로에서는 서명되지 않은 EXE 배포 금지.
- 베타 단계에서는 `unsigned` 허용 가능하나, 고객 전달 파일에는 항상 SHA256 제공.
- release 브랜치(push) 및 release 대상 PR에서는 `WINDOWS_OV_CERT_SHA1`가 없으면 CI가 실패해야 합니다.
- release 브랜치(push) 및 release 대상 PR에서는 인증서 material(`WINDOWS_OV_CERT_PFX_BASE64`, `WINDOWS_OV_CERT_PASSWORD`)이 없으면 CI가 실패해야 합니다.
- 배포 검증 항목:
  - `dist/release-metadata.json`의 `signing_status`
  - `dist/SHA256SUMS.txt` 무결성 일치 (`newsletter_web.exe`, `release-metadata.json`, `support-bundle.zip`)

### 코드서명 파일럿 실행

```powershell
./scripts/devtools/sign_windows_exe.ps1 -ExePath "dist\newsletter_web.exe" -CertSha1 "<OV_CERT_SHA1>"
```

- CI secret:
  - `WINDOWS_OV_CERT_SHA1`: 인증서 Thumbprint
  - `WINDOWS_OV_CERT_PFX_BASE64`: OV 인증서 `.pfx` 파일의 base64 인코딩 값
  - `WINDOWS_OV_CERT_PASSWORD`: OV 인증서 `.pfx` 비밀번호
- release 브랜치에서는 signing required, main/feature 브랜치에서는 기본적으로 signing을 수행하지 않습니다(`unsigned`).

### GitHub-hosted runner 프로비저닝 기준

- release 경로에서는 아래 순서로 검증합니다.
  1. `WINDOWS_OV_CERT_SHA1` 존재 확인
  2. certificate store에서 thumbprint 조회
  3. store에 없으면 `WINDOWS_OV_CERT_PFX_BASE64` + `WINDOWS_OV_CERT_PASSWORD`로 임시 import
  4. import 후 thumbprint 일치 확인
  5. self-signed dry-run 인증서인 경우 CI runner에서 `CurrentUser\\Root`, `CurrentUser\\TrustedPublisher` 신뢰 저장소를 임시 보강
- 2~4 과정 중 하나라도 실패하면 sign 단계로 넘어가지 않고 CI를 즉시 실패 처리합니다.

#### 운영 준비 예시 (PFX -> GitHub Secret)

```bash
# macOS/Linux
base64 -i windows-ov-cert.pfx | tr -d '\n' > windows-ov-cert.base64.txt
```

- `windows-ov-cert.base64.txt` 내용을 `WINDOWS_OV_CERT_PFX_BASE64`에 등록
- `.pfx` 비밀번호를 `WINDOWS_OV_CERT_PASSWORD`에 등록

## 2) 업데이트 정책 (반자동 + 체크섬)

- 배포 단위:
  - `newsletter_web.exe`
  - `release-metadata.json`
  - `SHA256SUMS.txt`
  - `update-manifest.json` (release 경로 필수)
  - `support-bundle.zip` (지원 요청 시)
- `SHA256SUMS.txt`는 최소 `newsletter_web.exe`, `release-metadata.json`, `support-bundle.zip`를 포함하며,
  `update-manifest.json` 생성 시 해당 파일 해시도 포함해야 합니다.
- 반자동 업데이트 절차:
  1. 운영팀이 새 버전을 배포 포털에 게시
  2. `update-manifest.json`의 `download_url`/`sha256` 기준으로 배포 파일 확인
  3. `SHA256SUMS.txt` 기준으로 무결성 검증
  4. 기존 EXE 백업 후 신규 EXE 교체

## 3) 장애 대응 SLA(초안)

- P0(서비스 실행 불가/데이터 손실 위험): 4시간 내 1차 대응, 1영업일 내 복구 목표
- P1(핵심 기능 실패): 1영업일 내 대응
- P2(우회 가능한 기능 저하): 3영업일 내 대응

## 4) 지원 진단 번들 표준

- 생성 명령:

```bash
python scripts/devtools/create_support_bundle.py --artifact dist/newsletter_web.exe --dist-dir dist --output dist/support-bundle.zip
```

- 포함 항목:
  - `system-info.json`
  - `bundle-manifest.json`
  - `recent-errors.txt`
  - `release-metadata.json` (존재 시)
  - `SHA256SUMS.txt` (존재 시)
  - 최근 로그(최대 20개, 마스킹 적용)
- 마스킹 대상:
  - `*_KEY`, `*_TOKEN`, `*_SECRET`, `*_PASSWORD`, `Bearer ...`

## 5) 롤백 플레이북

1. 신규 EXE 배포 중단
2. 직전 안정 버전 EXE + 체크섬 재배포
3. 고객 측에서 EXE 교체 후 `/health` 확인
4. 재발 방지 이슈 등록(원인/대응/재현조건/방지책)

## 6) P0 CI 운영 기준

- branch protection required check:
  - `main`: `Build Check (windows-latest)`
  - `release`: `Build Check (windows-latest)`
  - `release/*`: `Build Check (windows-latest)`
  - 관리자 우회 방지(`isAdminEnforced=true`)를 유지
- burn-in 기준:
  - 최근 10회 `Build Check (windows-latest)` 성공률 95% 이상
  - `cancelled/skipped/neutral/unknown` 결론은 burn-in 샘플에서 제외(중복 런 취소/진행중 런 노이즈 제거)
- 측정 명령:

```bash
python scripts/devtools/windows_ci_burnin_report.py --workflow "Main CI Pipeline" --branch main --limit 10 --min-success-rate 95 --ignore-conclusions cancelled,skipped,neutral,unknown
```

- GitHub release control 점검 명령:

```bash
make github-windows-release-controls
```

## 7) 작업 단위 운영 규칙 (필수)

- Windows release 관련 작업은 반드시 `Branch -> Commit -> PR -> CI -> Merge` 순서로 진행합니다.
- 단위 분할 기준:
  - 코드/문서 변경: 1 Delivery Unit = 1 PR
  - GitHub 관리자 설정(브랜치 보호/시크릿/변수): 단독 PR로 증적 문서를 남기고, PR 본문에 실제 적용 시각/명령/결과를 기록
- PR 머지 전 필수 증적:
  - `make github-windows-release-controls`
  - release dry-run 실행 링크
  - 실패 시 원인/차단 상태/롤백 메모

## 8) 실행 로그

- 2026-02-24 실행 로그: `docs/setup/WINDOWS_RELEASE_ADMIN_LOG_2026-02-24.md`
