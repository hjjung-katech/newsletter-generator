# Windows EXE 운영 정책

작성일: 2026-02-24

## 1) 코드서명 정책 (OV)

- 목표: GA(정식 배포) 경로에서는 서명되지 않은 EXE 배포 금지.
- 베타 단계에서는 `unsigned` 허용 가능하나, 고객 전달 파일에는 항상 SHA256 제공.
- release 브랜치에서는 `WINDOWS_OV_CERT_SHA1`가 없으면 CI가 실패해야 합니다.
- 배포 검증 항목:
  - `dist/release-metadata.json`의 `signing_status`
  - `dist/SHA256SUMS.txt` 무결성 일치

### 코드서명 파일럿 실행

```powershell
./scripts/devtools/sign_windows_exe.ps1 -ExePath "dist\newsletter_web.exe" -CertSha1 "<OV_CERT_SHA1>"
```

- CI secret:
  - `WINDOWS_OV_CERT_SHA1`: 인증서 Thumbprint
- release 브랜치에서는 signing required, main/feature 브랜치에서는 optional.

## 2) 업데이트 정책 (반자동 + 체크섬)

- 배포 단위:
  - `newsletter_web.exe`
  - `release-metadata.json`
  - `SHA256SUMS.txt`
  - `update-manifest.json`
  - `support-bundle.zip` (지원 요청 시)
- 반자동 업데이트 절차:
  1. 운영팀이 새 버전을 배포 포털에 게시
  2. 고객/지원팀이 EXE 다운로드
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

- `main` branch protection required check:
  - `Build Check (windows-latest)`
- burn-in 기준:
  - 최근 10회 `Build Check (windows-latest)` 성공률 95% 이상
  - `cancelled/skipped/neutral/unknown` 결론은 burn-in 샘플에서 제외(중복 런 취소/진행중 런 노이즈 제거)
- 측정 명령:

```bash
python scripts/devtools/windows_ci_burnin_report.py --workflow "Main CI Pipeline" --branch main --limit 10 --min-success-rate 95 --ignore-conclusions cancelled,skipped,neutral,unknown
```
