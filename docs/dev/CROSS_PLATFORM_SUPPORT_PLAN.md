# Cross-Platform 지원 전략 (Linux / macOS / Windows)

## 1) 현재 코드베이스 진단 요약

현재 저장소는 **런타임(Flask 웹/CLI)** 자체는 Python 기반으로 운영체제 독립성이 상당 부분 확보되어 있지만,
개발 워크플로우/배포/운영 스크립트 레이어에서 Windows 중심 흔적이 강합니다.

핵심 관찰:

- `Makefile`의 기본 경로/venv 가정이 macOS 특정 경로와 POSIX shell 전제를 내장하고 있습니다.
- 릴리즈 파이프라인은 `build-web-exe`, `windows-release-artifacts` 등 **Windows EXE 아티팩트 중심**으로 설계되어 있습니다.
- 문서 및 devtool이 Windows 바이너리 운영 문서 중심으로 풍부하고, Linux/macOS 배포 아티팩트 표준은 상대적으로 약합니다.
- `web/path_manager.py`, `web/binary_compatibility.py`처럼 PyInstaller/frozen 환경 고려는 있지만,
  제품 전략 관점에서 “OS별 배포 목표(예: wheel/docker/native bundle)”가 아직 명확히 분리되어 있지 않습니다.

---

## 2) 전략 목표 (Product + Engineering)

### Product 목표

1. **동일한 사용자 경험**: Windows, Linux, macOS에서 동일 명령으로 실행/테스트/배포.
2. **배포 옵션 명확화**:
   - 서버 운영: Docker + Flask canonical
   - 데스크톱형 배포: OS별 native bundle(필요 시)
3. **지원 정책 명시**: 지원 OS/버전, Python 버전, 기능 차등(예: EXE는 Windows만) 공식화.

### Engineering 목표

1. 운영체제 의존 로직을 `core runtime`과 `platform adapter`로 분리.
2. CI matrix를 통해 OS별 회귀를 자동 검증.
3. 경로/프로세스/인코딩/셸 의존성을 표준 라이브러리 중심으로 통일.

---

## 3) 아키텍처 접근법

### A. 플랫폼 추상화 계층 도입

`newsletter/platform/` (신규) 같은 얇은 계층에 아래를 집중합니다.

- `paths.py`: 경로 계산, writable 디렉토리 정책
- `process.py`: subprocess 호출 옵션, timeout, shell 사용 금지 기본값
- `terminal.py`: ANSI 출력/인코딩/TTY 감지
- `packaging.py`: frozen 여부, 리소스 위치 계산

기존 코드에서는 `os.name`, `sys.platform` 직접 분기 대신 이 계층을 사용합니다.

### B. 실행 모델 분리

1. **Canonical runtime (권장)**: Flask + Gunicorn/Uvicorn-worker + Docker
2. **Developer runtime**: `python -m apps.web.main` / `make check`
3. **Desktop binary runtime**: Windows EXE는 유지하되, Linux/macOS는 우선순위에 따라 별도 bundle 전략 검토

### C. 배포 전략 이원화

- **서버 배포 표준화**: Docker 이미지를 1차 산출물로 고정 (OS 중립)
- **클라이언트 배포 선택형**: Windows EXE를 특수 경로로 유지, macOS/Linux native bundle은 비용-효익 검토 후 단계적 도입

---

## 4) 구현 로드맵 (권장 4단계)

## Phase 0 — 기준선 수립 (1주)

- OS 의존 코드 전수 조사(정규식 + import graph)
- “차단 이슈” 분류:
  - hard-coded path
  - shell/bash 종속
  - PowerShell/.bat 종속
  - 인코딩/개행 가정
- Cross-platform 정책 문서 초안 작성

**산출물**
- `docs/dev/CROSS_PLATFORM_SUPPORT_PLAN.md` 확정판
- 이슈 백로그(epic + tickets)

## Phase 1 — 개발/테스트 환경 중립화 (1~2주)

- `Makefile`의 환경 의존 값 제거 (`EXPECTED_CWD` 외부화, python 경로 탐색 개선)
- `scripts/devtools`에 OS 중립 엔트리포인트 추가 (Python wrapper 우선)
- `.sh/.bat/.ps1`는 thin wrapper로 축소하고 실제 로직은 Python으로 일원화
- 테스트 실행 명령 표준화 (`python -m pytest ...`)

**완료 기준**
- macOS/Linux/Windows에서 `bootstrap`, `check` 동작

## Phase 2 — 런타임/패키징 정리 (2~3주)

- `web/path_manager.py`, `web/binary_compatibility.py`, `web/runtime_hook.py`의
  플랫폼 분기 규칙을 플랫폼 계층으로 이전
- 리소스 경로 계산을 `pathlib` 기반으로 통일
- frozen/non-frozen 시나리오를 OS별 테스트 추가

**완료 기준**
- Flask 웹 런타임이 3개 OS에서 동일 API contract로 동작
- MOCK_MODE 기반 스모크 테스트 3개 OS CI 통과

## Phase 3 — CI/CD 및 릴리즈 체계 확장 (1~2주)

- GitHub Actions matrix: `ubuntu-latest`, `macos-latest`, `windows-latest`
- 필수 게이트 분리:
  - 공통 게이트(3 OS): lint + unit + web smoke(mock)
  - 플랫폼 게이트(Windows 전용): EXE 빌드/서명/무결성
- Release manifest에 OS별 산출물 명세 추가

**완료 기준**
- main 브랜치 PR마다 3 OS CI pass
- 릴리즈 시 OS별 아티팩트/지원 정책 자동 검증

---

## 5) 우선순위 Backlog (Top 10)

1. `Makefile`의 `EXPECTED_CWD` 절대경로 제거/외부화
2. `make doctor`의 POSIX shell 구문을 Python 스크립트로 대체
3. Windows 전용 빌드 타깃을 `platform-specific` 섹션으로 격리
4. `scripts/devtools/*` 중 핵심 진입점을 Python 단일 엔트리로 통일
5. 경로 연산 전수 `pathlib` 통일
6. 플랫폼 감지 유틸 단일화 (`platform.system()` 래퍼)
7. 인코딩 정책(UTF-8) 공통 초기화 모듈 추가
8. `.env` 로딩 책임 일원화 (import-time side effect 방지)
9. OS matrix CI + 캐시 전략(pip cache) 적용
10. 운영 문서(설치/문제해결) Linux/macOS 절차 정본화

---

## 6) 리스크 및 대응

- **리스크 1: Windows EXE 경로 회귀**
  - 대응: Windows 전용 contract/smoke를 별도 고정, 공통 리팩터와 분리 머지
- **리스크 2: 경로/권한 차이로 런타임 장애**
  - 대응: temp/log/output writable 정책을 OS별 표준 디렉토리로 테스트
- **리스크 3: CI 시간 증가**
  - 대응: 빠른 PR 게이트(필수) + 야간 풀 게이트(확장) 이원화
- **리스크 4: 문서-코드 불일치**
  - 대응: docs/config consistency 체크를 CI 필수화

---

## 7) KPI / 성공 지표

- 3 OS에서 `make check` 성공률 95%+
- OS별 이슈 재현률 감소(“Windows에서만/리눅스에서만” 클래스)
- 신규 기능 PR의 OS 관련 Hotfix 비율 감소
- 릴리즈 리드타임(테스트~배포) 안정화

---

## 8) 실행 원칙

- Flask + Postmark canonical stack 유지
- MOCK_MODE 기본 테스트 원칙 유지
- web runtime API 응답 스키마 불변 (`status`, `html_content`, `title`, `generation_stats`, `input_params`, `error`)
- 고위험 영역(설정/스케줄러/메일 경로)은 작은 PR 단위로 점진적 변경

