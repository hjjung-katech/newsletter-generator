# Cross-Platform Engineering Plan (Windows + macOS + Linux)

이 문서는 "방향성"이 아니라 **현 코드베이스 기준으로 바로 실행 가능한 기술 적용 계획**을 정의합니다.
특히 요청하신 관점(코어 런타임/플랫폼 어댑터 분리, OS별 CI 회귀 메트릭, 경로/프로세스/인코딩/셸 의존성 표준화)을 중심으로 작성했습니다.

- 기준일: 2026-03-14
- 목표:
  - Windows 중심 전달 구조를 macOS/Linux까지 확장
  - macOS/Windows에서 one-click(백엔드+프론트엔드 동시 구동) 제품 제공
  - Flask + Postmark canonical runtime 및 ops-safety 계약 유지

---

## 1) 현 코드베이스 사실 기반 진단 (As-Is)

### 1.1 이미 갖춘 기반

1) **Frozen/Source 경로 분기 기반 존재**
- `web/runtime_paths.py`가 PyInstaller(frozen) vs source 실행 경로를 분기합니다.
- 템플릿/정적파일/DB/.env 위치를 runtime-aware하게 선택합니다.

2) **Windows 바이너리 릴리즈 파이프라인 성숙**
- `Makefile`에 `build-web-exe`, `windows-release-artifacts`, `windows-sign-exe`, `validate-windows-release-artifacts` 타겟이 정리돼 있습니다.
- 즉, "빌드-서명-체크섬-검증" 체인이 Windows에는 이미 구현되어 있습니다.

3) **CI에서 cross-platform source smoke 이미 수행**
- `main-ci.yml`에서 source smoke는 `ubuntu-latest`, `macos-latest`, `windows-latest`를 모두 포함합니다.
- Build Check는 ubuntu/windows 중심이며 Windows EXE smoke가 별도 존재합니다.

### 1.2 현재 구조의 기술 부채/갭

1) **Runtime Path 계층의 이원화**
- `web/runtime_paths.py`(pathlib 중심)와 `web/binary_compatibility.py`(os.path 중심)가 유사 책임을 나눠 가짐.
- 기능 중복은 장기적으로 OS별 drift(한쪽만 고쳐지는 회귀)를 만듭니다.

2) **Entrypoint 기본 포트 비일관성**
- source runtime 기본 포트 정책(문서상 8000 계열)과 Windows EXE entrypoint 기본 포트(5000)가 공존.
- 운영 측면에서 smoke/문서/진단 가이드가 갈라질 가능성이 있습니다.

3) **패키징 스크립트의 OS 표준화 부족**
- `build_web_exe_enhanced.py`는 Windows 성공 사례이지만, path/process/encoding 규약이 "공통 규약"으로 문서화되어 있지 않습니다.
- macOS/Linx 확장 시 동일한 규약을 강제할 장치가 필요합니다.

4) **CI 결과는 있으나 "회귀 메트릭"은 약함**
- job pass/fail은 있으나, 플랫폼별 KPI(부팅시간 p95, smoke 성공률, 바이너리 부팅 실패 유형 분포 등)는 정량 추적이 약합니다.

---

## 2) 핵심 설계 원칙 (Technical North Star)

### 원칙 A — Core Runtime / Platform Adapter 엄격 분리

- **Core Runtime (OS-neutral)**
  - Flask app, 생성/전송 도메인 로직, 스케줄/idempotency/outbox 계약
  - `newsletter_core` + `web`의 비즈니스 로직 계층
- **Platform Adapter (OS-specific)**
  - 프로세스 시작/종료, 파일 경로, 번들 리소스 해석, 브라우저 열기, 코드서명/업데이트
  - Windows/macOS/Linux 별 런처 및 packaging layer

> 목표: "비즈니스 동작"은 OS와 무관하게 동일, "실행 껍데기"만 OS별 분기.

### 원칙 B — 표준 라이브러리 우선

- 경로: `pathlib.Path`
- 프로세스: `subprocess.run(..., shell=False)`
- 인코딩: `encoding='utf-8'` 명시
- 플랫폼 분기: `sys.platform` 또는 `platform.system()`을 adapter 계층에만 허용

### 원칙 C — 측정 가능한 CI 회귀 체계

- pass/fail을 넘어 OS별 품질지표를 JSON artifact로 수집
- 최소 지표: smoke_success_rate, startup_latency_p95, crash_on_boot_rate, bundle_smoke_pass

---

## 3) 목표 아키텍처 (To-Be)

### 3.1 계층 구조

1. `runtime_core` (신규 개념 계층)
- 계약:
  - 설정 로딩 결과
  - 서버 시작/종료 인터페이스
  - health endpoint 확인 인터페이스
- 구현은 기존 `web.app`/`newsletter_core`를 재사용

2. `platform_adapters`
- `windows_adapter`
- `macos_adapter`
- `linux_adapter`

각 어댑터 책임:
- 번들/소스 경로 매핑
- 단일 인스턴스 락
- 브라우저 오픈
- 종료 시그널 처리
- OS별 배포 아티팩트 메타

3. `packaging_pipeline`
- Windows: 기존 PyInstaller + signing 체계 유지/정리
- macOS: `.app` + codesign/notarize 체인 추가
- Linux: 기본은 source/server 유지, desktop은 요구기반

### 3.2 핵심 인터페이스 초안

```text
RuntimeBootstrap
- resolve_paths() -> RuntimePaths
- prepare_environment() -> EnvResult
- launch_server() -> ProcessHandle
- wait_until_healthy(timeout_s)
- open_ui(url)
- shutdown(graceful_timeout_s)
```

각 OS adapter는 동일 인터페이스를 구현하고, Core Runtime은 해당 인터페이스만 호출합니다.

---

## 4) 실행 계획 (기술 적용 중심)

### Phase 0 (1주): 분석 고정 + 계약 테스트 먼저

- [ ] `runtime path/process/encoding/shell` 인벤토리 스캔 스크립트 추가(문서/리포트 생성)
- [ ] `runtime_paths` vs `binary_compatibility` 책임 매트릭스 작성
- [ ] 포트/경로/종료 동작 contract test 정의

**완료 기준**
- "어디서 OS 분기하는지"가 파일 단위로 식별됨
- 공통 인터페이스에 필요한 최소 계약 테스트가 생성됨

### Phase 1 (2주): Runtime Core / Adapter 경계 도입

- [ ] `runtime_core/bootstrap.py`(가칭) 도입
- [ ] Windows 기존 entrypoint를 adapter 호출 구조로 전환(동작 동일성 유지)
- [ ] `web/runtime_paths.py`를 경로 SSOT로 승격하고 중복 로직 축소

**완료 기준**
- source/frozen 부팅 로직의 주경로가 단일화
- 기존 Windows EXE smoke가 회귀 없이 통과

### Phase 2 (2주): 표준화 리팩터링 (Path/Process/Encoding/Shell)

- [ ] pathlib 표준화(신규 코드 os.path 금지)
- [ ] subprocess 표준 wrapper 통일(`shell=False` 기본)
- [ ] 파일 입출력 UTF-8 명시 규칙 적용
- [ ] Bash/PowerShell 전용 스크립트의 Python 대체 가능 영역 분리

**완료 기준**
- lint 또는 custom check로 규칙 위반 탐지 가능
- Windows/macOS/Linux source smoke 동시 green

### Phase 3 (2~3주): macOS One-Click MVP

- [ ] macOS adapter + `.app` 생성 파이프라인
- [ ] 더블클릭 실행 -> health OK -> 브라우저 오픈 smoke 구축
- [ ] 로그/DB/.env 경로를 macOS 사용자 권한 모델에 맞게 조정

**완료 기준**
- macOS 번들 smoke가 CI에서 재현 가능
- 수동 설치 문서 없이도 실행 가능한 MVP 제공

### Phase 4 (2주): CI 메트릭 + 릴리즈 신뢰성

- [ ] OS별 런타임 메트릭 수집 스크립트 추가(JSON artifact)
- [ ] 최근 N회 추세 리포트(회귀 감지)
- [ ] macOS signing/notarization과 release evidence 템플릿 확정

**완료 기준**
- "성공/실패"뿐 아니라 "성능/안정성 추세"가 리뷰 가능
- 릴리즈 승인 기준이 정량화

---

## 5) CI 회귀 메트릭 설계 (요청 반영 핵심)

### 5.1 수집 지표

- `source_smoke_pass_rate_by_os`
- `bundle_smoke_pass_rate_by_os`
- `startup_latency_ms_p50/p95_by_os`
- `boot_failure_reason_distribution_by_os`
- `graceful_shutdown_success_rate_by_os`

### 5.2 품질 게이트 제안

- PR 게이트: source smoke 3OS 전부 green
- Desktop 관련 변경 PR:
  - Windows bundle smoke 필수
  - macOS bundle smoke(도입 후) 필수
- 릴리즈 게이트:
  - 최근 10회 기준 startup latency p95 임계치 이내
  - boot crash rate 임계치 이하

### 5.3 구현 방법

- 각 smoke 스크립트가 실행 결과를 공통 JSON schema로 출력
- workflow 마지막 단계에서 aggregation 스크립트로 summary 생성
- summary를 `GITHUB_STEP_SUMMARY` + artifact 업로드

---

## 6) 표준화 체크리스트 (경로/프로세스/인코딩/셸)

### 경로(Path)
- 신규/변경 파일에서 `pathlib` 우선
- 절대경로 계산은 adapter 또는 runtime_paths 모듈에서만

### 프로세스(Process)
- subprocess 호출은 공통 유틸 경유
- `shell=True` 사용 금지(예외는 보안/호환 사유 문서화)

### 인코딩(Encoding)
- 텍스트 파일 입출력 UTF-8 명시
- 로그/리포트 아티팩트도 UTF-8 고정

### 셸 의존성(Shell)
- Bash/PowerShell 전용 구현은 최소화
- 가능한 한 Python 스크립트로 통일
- OS별 shell 스크립트는 adapter/ops 계층으로 한정

---

## 7) 리스크와 완화

1) **분리 작업 중 회귀 리스크**
- 완화: contract test 선행 + 점진 이관(Windows baseline 보호)

2) **macOS 번들 보안 정책 리스크(codesign/notarize)**
- 완화: MVP 단계부터 CI에 서명검증 dry-run 슬롯 확보

3) **OS별 실행환경 편차 리스크**
- 완화: CI metric 기반 "회귀 조기 탐지" 운영

---

## 8) 90일 상세 로드맵 (실행 가능한 수준)

### Day 1~30
- runtime 경계 정의
- contract test 구축
- Windows 경로를 adapter 인터페이스로 감싸기

### Day 31~60
- path/process/encoding/shell 표준화
- macOS adapter MVP + bundle smoke

### Day 61~90
- macOS signing/notarization
- CI metric aggregation + release approval 기준 고정

---

## 9) 결론 (이번 개정의 핵심)

이 계획의 핵심은 "새 기술 도입"보다 **기존 자산을 공통 런타임 계약으로 재편**하는 것입니다.

- 먼저 Core Runtime / Platform Adapter를 분리해 구조적 안정성을 확보하고,
- 그 위에 macOS one-click MVP를 얹고,
- 마지막으로 CI 메트릭으로 운영 신뢰성을 계량화하면,

현재 코드베이스를 크게 흔들지 않으면서도 요청하신 크로스플랫폼 제품 목표에 가장 안전하게 도달할 수 있습니다.
