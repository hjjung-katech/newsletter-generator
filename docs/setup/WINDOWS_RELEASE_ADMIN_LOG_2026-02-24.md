# Windows Release Admin Log (2026-02-24)

## 목적

- Windows EXE release 제어 항목을 운영 환경에 적용한 이력을 남깁니다.
- GitHub 관리자 설정 변경도 PR 증적으로 추적하기 위한 기준 로그입니다.

## 추적 정보

- RR: #137
- Delivery Unit ID: `DU-20260224-windows-release-governance`

## 변경 요약

1. Branch protection 고정
   - 패턴: `main`, `release`, `release/*`
   - 필수 체크: `Build Check (windows-latest)`
   - 관리자 강제: `isAdminEnforced=true`
2. 배포 변수 설정
   - repo variable: `WINDOWS_UPDATE_BASE_URL` 설정 완료
   - production environment variable: `WINDOWS_UPDATE_BASE_URL` 설정 완료
3. release dry-run 실행
   - run: `22373389305`
   - 결과: 실패(의도된 차단)
   - 차단 원인: `WINDOWS_OV_CERT_SHA1` 미설정으로 서명 단계 실패

## 운영 판단

- 현재 차단은 정상입니다.
- release 경로에서 서명 시크릿이 없으면 배포를 막아야 한다는 정책이 제대로 동작합니다.

## 남은 조치

1. `WINDOWS_OV_CERT_SHA1` 운영값을 repo secret으로 설정
2. release dry-run 재실행
3. `sign -> smoke -> update-manifest -> checksum/validate` 전 단계 통과 확인

## 2026-02-25 업데이트

1. 임시 dry-run signing secret(`WINDOWS_OV_CERT_SHA1`, `WINDOWS_OV_CERT_PFX_BASE64`, `WINDOWS_OV_CERT_PASSWORD`) 등록
2. release dry-run 실행: `22376468136`
3. 실패 원인:
   - `Provision Windows signing certificate` 단계에서 `Import-PfxCertificate` 반환값이 단일 객체일 때 `.Count` 접근 오류 발생
4. 대응:
   - `scripts/devtools/provision_windows_signing_cert.ps1`에서 단일/배열 반환을 모두 처리하도록 hotfix 적용

## 2026-02-25 추가 업데이트

1. main 머지 후 release dry-run 재실행: `22377306953` (`release/dry-run-20260225-4`)
2. 실패 원인:
   - `Sign Windows artifact (OV pilot)` 단계에서 `signtool verify /pa`가 self-signed dry-run 인증서를 신뢰 체인으로 검증하지 못해 실패
3. 대응:
   - `scripts/devtools/provision_windows_signing_cert.ps1`에서 self-signed 인증서 감지 시 CI runner `CurrentUser\\Root`, `CurrentUser\\TrustedPublisher` 저장소를 임시 보강하도록 수정

## 2026-02-25 추가 업데이트 2

1. 최신 main 기준 release dry-run 재실행: `22377896633` (`release/dry-run-20260225-5`)
2. 관찰:
   - `Provision Windows signing certificate` 단계가 비정상 장기 실행되어 run 취소
3. 대응:
   - provisioning 경로의 self-signed 신뢰 저장소 주입을 제거
   - `scripts/devtools/sign_windows_exe.ps1`에서 self-signed dry-run 인증서에 대해 thumbprint 기반 fallback 검증 로직으로 대체

## 2026-02-25 추가 업데이트 3

1. 최신 main 기준 release dry-run 재실행: `22378547592` (`release/dry-run-20260225-6`)
2. 실패 원인:
   - self-signed fallback 검증은 성공했으나, 직전 `signtool verify`의 `LASTEXITCODE=1`가 유지되어 step이 실패 처리
3. 대응:
   - fallback 검증 성공 시 `LASTEXITCODE`를 `0`으로 명시 리셋하도록 수정

## 2026-02-25 추가 업데이트 4

1. 최신 main 기준 release dry-run 재실행: `22379041439` (`release/dry-run-20260225-7`)
2. 결과:
   - `Build Check (windows-latest)` 성공
   - `Sign -> Smoke -> update-manifest -> checksum/validate` 전 단계 성공
3. 임시 dry-run 브랜치 정리:
   - 로컬: `release/dry-run-20260225-4~7` 삭제
   - 원격: `release/dry-run-20260224-1`, `release/dry-run-20260224-2`, `release/dry-run-20260225-3~7` 삭제
4. 보호 규칙 처리:
   - 정리 작업을 위해 `release/*`의 `allowsDeletions`를 임시 `true`로 전환 후 즉시 `false` 원복
   - 최종 상태: `main`, `release`, `release/*` 모두 `required check=Build Check (windows-latest)`, `requiredApprovingReviewCount=1`, `isAdminEnforced=true`, `allowsDeletions=false`
5. 남은 운영 조치:
   - `WINDOWS_OV_CERT_*`를 실제 운영 OV 인증서 값으로 교체 필요(현재 값은 dry-run 인증서 기준)

## 롤백 메모

- branch protection 롤백: GitHub Branch Protection에서 대상 패턴의 required check/admin enforcement를 원복
- variable 롤백: `WINDOWS_UPDATE_BASE_URL`를 기존값으로 되돌리거나 삭제
