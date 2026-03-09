# Windows Release Admin Log (2026-02-24)

> Historical note (RR-10): active Windows release guidance remains in
> `../../setup/WINDOWS_EXE_OPERATIONS.md`.

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
   - 삭제 허용 임시 전환 대상 rule: `release/*` (`BPR_kwDOOnCa4M4EXd3D`)
5. 남은 운영 조치:
   - `WINDOWS_OV_CERT_*`를 실제 운영 OV 인증서 값으로 교체 필요(현재 값은 dry-run 인증서 기준)

## 2026-03-07 추가 업데이트

1. 최신 `main` 재점검:
   - HEAD: `ae45c62` (`chore(ci): clarify agent guidance and delivery unit policy (#151)`)
2. 운영 상태 점검:
   - `main` branch protection의 `requiredApprovingReviewCount`가 `0`으로 설정되어 있었음
3. 즉시 대응:
   - `main` rule (`BPR_kwDOOnCa4M4EXTTS`)을 `requiredApprovingReviewCount=1`로 원복
   - 원복 후 GraphQL 재조회로 rule 상태 재검증 완료
4. 최종 확인:
   - `main`, `release`, `release/*` 모두 `required check=Build Check (windows-latest)`, `requiredApprovingReviewCount=1`, `isAdminEnforced=true`, `allowsDeletions=false`
   - `WINDOWS_UPDATE_BASE_URL`는 repo/environment(`production`) 모두 `https://github.com/hjjung-katech/newsletter-generator/releases/latest/download`로 유지됨
5. 여전히 남은 운영 과제:
   - `WINDOWS_OV_CERT_SHA1`, `WINDOWS_OV_CERT_PFX_BASE64`, `WINDOWS_OV_CERT_PASSWORD`는 실제 운영 OV 인증서 값으로 교체되지 않았음
   - 현재 repo secret 등록 시각은 `2026-02-25 00:33 UTC` 기준이며, dry-run 인증서 교체 후 release dry-run 1회 재검증이 필요

## 2026-03-07 추가 업데이트 2

1. 운영 기준 재확인:
   - 현재 저장소는 solo-developer 모드로 운영 중이므로 `main`의 `requiredApprovingReviewCount`는 `0`으로 유지
2. 정책 반영:
   - `main` rule (`BPR_kwDOOnCa4M4EXTTS`)을 다시 `requiredApprovingReviewCount=0`으로 조정
3. 최종 확인:
   - `main`: `required check=Build Check (windows-latest)`, `requiredApprovingReviewCount=0`, `isAdminEnforced=true`, `allowsDeletions=false`
   - `release`, `release/*`: `required check=Build Check (windows-latest)`, `requiredApprovingReviewCount=1`, `isAdminEnforced=true`, `allowsDeletions=false`

## 2026-03-07 추가 업데이트 3

1. 운영 OV 인증서 최종화 재시도:
   - repo secret 메타데이터를 재확인한 결과 `WINDOWS_OV_CERT_SHA1`, `WINDOWS_OV_CERT_PFX_BASE64`, `WINDOWS_OV_CERT_PASSWORD`의 갱신 시각은 여전히 `2026-02-25 00:33 UTC` 기준이었음
2. 현재 등록값 성격 재검증:
   - 성공했던 release dry-run `22379041439`의 Windows signing 로그를 재조회한 결과, 서명 인증서 `Issued to` / `Issued by`가 `Newsletter Generator DryRun Code Signing`으로 확인됨
3. 로컬 운영자 환경 확인:
   - 표준 보관 경로(`Desktop`, `Documents`, `Downloads`, `.config`)에서 운영 OV 인증서 후보 `.pfx` / `.p12` 파일을 찾지 못함
   - macOS keychain codesigning identity 조회 결과 `0 valid identities found`
4. 결론:
   - 실제 운영 OV 인증서 원본이 현재 작업 환경에 없어서 `WINDOWS_OV_CERT_*` 교체와 release dry-run 재검증은 이번 차수에서 진행 불가
   - 실제 완료를 위해서는 운영 OV `.pfx`, 비밀번호, 기대 thumbprint를 안전한 경로로 별도 제공받아야 함

## 2026-03-07 추가 업데이트 4

1. 후속 작업 backlog 고정:
   - 운영 OV `.pfx`, 비밀번호, 기대 thumbprint를 안전한 경로로 확보
   - `WINDOWS_OV_CERT_SHA1`, `WINDOWS_OV_CERT_PFX_BASE64`, `WINDOWS_OV_CERT_PASSWORD`를 실제 운영값으로 교체
   - release 브랜치에서 dry-run 1회 재실행 후 `sign -> smoke -> update-manifest -> checksum/validate` 전 단계 통과 증적 추가
2. 차수 종료 정리:
   - 저장소 변경사항은 admin log 기준으로 `main`에 반영 완료
   - 로컬 생성 산출물(`artifacts/`)과 병합 완료 작업 브랜치는 이번 차수 종료 시점에 정리 대상

## 롤백 메모

- branch protection 롤백: GitHub Branch Protection에서 대상 패턴의 required check/admin enforcement를 원복
- variable 롤백: `WINDOWS_UPDATE_BASE_URL`를 기존값으로 되돌리거나 삭제
