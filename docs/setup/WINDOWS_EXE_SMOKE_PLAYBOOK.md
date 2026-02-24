# Windows EXE Smoke 장애 대응 플레이북

작성일: 2026-02-24

## 목표

- CI `Windows EXE health smoke` 실패 시 30분 내 원인 분류를 완료합니다.
- 분류 축: 빌드 실패 / 실행 실패 / 헬스체크 실패 / 종료·정리 실패.

## 표준 실행

```powershell
python scripts/devtools/build_web_exe_enhanced.py
./scripts/devtools/windows_exe_smoke.ps1 -ExePath "dist\newsletter_web.exe" -BaseUrl "http://127.0.0.1:5000" -TimeoutSeconds 120
```

## 장애 유형별 조치

### 1) `EXE not found`

- 원인 후보:
  - PyInstaller build 실패
  - `dist` 경로 변경/정리됨
- 즉시 조치:
  1. build 단계 로그 확인
  2. `dist/newsletter_web.exe` 생성 여부 확인
  3. 빌드 스크립트 canonical 경로 확인 (`build_web_exe_enhanced.py`)

### 2) `EXE exited early`

- 원인 후보:
  - 런타임 import/path 오류
  - 필수 설정 미존재
- 즉시 조치:
  1. 콘솔/로그에서 traceback 확인
  2. `web/runtime_hook.py` 로딩 메시지 확인
  3. `dist/.env` 및 템플릿/정적 파일 배치 확인

### 3) `Health smoke timed out`

- 원인 후보:
  - 서버 기동 지연
  - 포트 충돌(5000)
  - `/health` 핸들러 초기화 실패
- 즉시 조치:
  1. 포트 점유 프로세스 확인
  2. `TimeoutSeconds` 임시 상향으로 기동 지연 여부 분리
  3. `/health` 응답 상태(`healthy|degraded`) 확인

### 4) 프로세스 종료/정리 실패

- 원인 후보:
  - child process 미정리
  - Windows signal 처리 이슈
- 즉시 조치:
  1. 강제 종료 후 포트 해제 확인
  2. graceful shutdown 로그 확인
  3. 재시작 후 동일 증상 재현 여부 확인

## 수집 증적

- 필수:
  - 실패 run URL
  - smoke 스크립트 stdout/stderr
  - `dist/release-metadata.json`
  - `dist/support-bundle.zip`
- 권장:
  - 실패 직전 커밋 SHA
  - 최근 성공 run과의 diff 범위

## 에스컬레이션 기준

- 연속 2회 이상 동일 유형 실패
- release 브랜치에서 smoke 실패
- customer-impact 가능성이 있는 실행 실패
