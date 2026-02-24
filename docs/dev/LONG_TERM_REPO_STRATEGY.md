# Long-term Repo Strategy & Operating Playbook

이 문서는 리포 구조/운영 정책의 장기 정본(SSOT)입니다.

- 기준일: 2026-02-23
- 적용 범위: repository structure, docs SSOT, repo hygiene automation, long-running execution model
- 연계 문서: `docs/dev/REPO_HYGIENE_POLICY.md` (Week 1 정책 기준선)
- 연계 스크립트: `scripts/repo_audit.py`, `scripts/repo_hygiene_policy.json`

## 1) 현재 상태 진단 (요약)

### 관찰된 구조적 이슈

- 루트 엔트리가 과다합니다 (기준 스냅샷: 총 55개, 파일 37/디렉터리 18).
- 실행/빌드/유틸 스크립트가 루트에 산재되어 있습니다.
  - 예: `build_web_exe.py`, `fix_env_setup.py`, `cleanup_debug_files.py`, `run_tests.py`
- 루트 문서와 `docs/` 문서의 역할이 일부 중복되어 진입점이 분산됩니다.
- 숨김 폴더(`.vscode`, `.agents`, `.release`, `.githooks`) 중 일부는 유지 가치가 있으나, 유지 근거가 기여자 관점에서 충분히 드러나지 않습니다.
- `docs/PROJECT_STRUCTURE.md` 일부 서술과 현재 체감 상태 간 괴리가 있어 구조 문서의 신뢰도가 떨어질 수 있습니다.

### 이미 잘 되어 있는 기반

- Canonical runtime과 환경변수 계약이 명확합니다.
  - `Flask + Postmark`, `POSTMARK_SERVER_TOKEN`, `EMAIL_SENDER`
- `make check`, `make check-full` 중심의 게이트 운영 철학이 정립되어 있습니다.
- release manifest 기반 검증 스크립트가 있어 구조 정리 시 안전장치로 활용 가능합니다.

## 2) 목표 상태 (Target State)

### A. 루트 디렉터리는 "제품 입구"만 남긴다

루트는 아래 5개 카테고리만 허용합니다.

1. 프로젝트 메타
- `README.md`, `LICENSE`, `CHANGELOG.md`, `CODEOWNERS`

2. 빌드/패키징
- `pyproject.toml`, `requirements*.txt`, `Makefile`

3. 운영 진입 파일(정책적으로 루트 고정된 소수)
- 예: `run_ci_checks.py`

4. 핵심 도메인 디렉터리
- `newsletter/`, `newsletter_core/`, `web/`, `tests/`, `docs/`, `scripts/`

5. 플랫폼 설정
- `.github/`, `.release/`, `.gitignore`

원칙:
- 그 외 루트 실행 파일은 `scripts/`(또는 필요 시 `tools/`)로 이동합니다.

### B. 단일 소스 정책(SSOT) 강화

- 환경변수/런타임 계약: `docs/reference/*`를 SSOT로 유지합니다.
- 리포지토리 구조 계약: 본 문서를 장기 구조 SSOT로 지정합니다.
- 코드/문서 불일치 시 CI에서 감지되도록 구조 검증 스크립트를 도입합니다.

### C. "대청소"가 아닌 "운영 안전형 정리"

- 운영 안전성(설정 단일화, idempotency/outbox)을 먼저 잠금한 뒤 구조 리팩토링 범위를 넓힙니다.
- 구조 변경은 small-batch(권장: 300 LOC 이하, 8 files 이하)로 분할합니다.

## 3) 3단계 로드맵 (12주)

### Phase 1 (1~3주): 인벤토리/정책 고정

목표:
- 무엇을 유지/이동/삭제/ignore 할지 기준을 먼저 고정합니다.

작업:
1. `scripts/repo_audit.py` 작성
- top-level 파일/디렉터리 분류
- tracked vs ignored vs local-only 구분
- orphan 문서/스크립트 후보 추출
2. 삭제/이관 정책 문서화
- 개인 IDE 설정은 ignore 기본, 팀 공통 설정만 예외 추적
- `.release`/`.github`/`.githooks` 유지 근거 명시
3. CI에 정책 체크 추가(초기 soft gate)
- 초기에는 warning-only

완료 조건 (DoD):
- 구조 정책 SSOT 문서 지정 완료
- 인벤토리 리포트가 CI artifact로 생성
- allowlist/denylist 팀 합의 완료

### Phase 2 (4~8주): 루트 슬림화 + 경로 정규화

목표:
- 사용자가 체감하는 "지저분함"을 실질적으로 해소합니다.

작업:
1. 루트 실행 스크립트 이동
- `build_*`, `fix_*`, `cleanup_*` 류를 `scripts/devtools/`로 이동
2. 문서 진입점 축소
- 루트 `README.md`는 개요 + 링크만 유지
- 상세 운영/개발 문서는 `docs/`로 집중
3. 파일명/위치 규칙 통일
- setup/bootstrap 류 명명 컨벤션 정렬
4. deprecated 경로 shim 추가 후 점진 제거
- 사용자/CI 호환 기간 부여

완료 조건 (DoD):
- 루트 엔트리 수 55 -> 30 이하
- 신규 기여자 onboarding 경로가 README만으로 5분 내 동작
- CI/배포 파이프라인 무중단

### Phase 3 (9~12주): 자동화 거버넌스 + 운영 플레이북

목표:
- "다시 지저분해지지 않게" 시스템화합니다.

작업:
1. Repo hygiene gate를 hard fail로 승격
2. ADR(Architecture Decision Record) 도입
- 구조/운영 의사결정 이력 관리
3. Ops-safety + 구조 리팩토링 연동
- 고위험 변경에 구조 체크 + 운영 체크 동시 요구
4. 릴리즈 체크리스트 표준화
- `scripts/release_preflight.py`와 문서/구조 체크 결합

완료 조건 (DoD):
- 구조 위반 PR 자동 차단
- ADR 누적 및 변경 근거 추적 가능
- 릴리즈 전 수동 점검 항목 최소화

## 4) "불필요한 .* 폴더" 정리 원칙

무조건 삭제가 아니라, 팀 가치/재현성 기준으로 판단합니다.

유지 (프로젝트 운영 필수):
- `.github/` (CI/CD)
- `.release/` (manifest 검증 체계)

조건부 유지 (팀 규칙 필요):
- `.vscode/` (팀 공통 task/settings만 추적)
- `.githooks/` (hook bootstrap 실제 사용 시)
- `.agents/` (에이전트 운영에 실질 사용 시)

기본 ignore/제거 대상:
- 개인 로컬 캐시/툴 상태 디렉터리
- 재생성 가능한 산출물

핵심 원칙:
- "숨김 폴더라서 제거"가 아니라, "팀 운영에 재현 가능한 가치가 있는가"로 결정합니다.

## 5) 스킬/에이전트 적극 활용 운영모델

"짧은 작업"이 아니라 "장기 실행"을 위해 프로토콜 기반으로 운영합니다.

### A. Workstream 기반 멀티 에이전트 운영

- Agent A (Repo Hygiene): 구조/이동/삭제 정책 + 자동화
- Agent B (Ops Safety): idempotency/outbox/설정 단일화 회귀 방지
- Agent C (Docs SSOT): 문서 정합성/중복 제거/링크 무결성
- Agent D (Release Guard): manifest/preflight/CI gate 동기화

각 Agent는 주 단위 deliverable + metric으로 병렬 운영합니다.

### B. Skill 실행 규칙

개발 사이클 기본 체인:
1. 인벤토리/계획 수립
2. 작은 배치 리팩토링
3. `make check`
4. `make check-full`
5. ops-safety 관련 테스트(해당 변경 시)

실패 시 반드시 rollback 기준과 원인 분류를 템플릿으로 남깁니다.

### C. 장기 운영 지표 (KPI)

Repo cleanliness KPI:
- 루트 엔트리 수
- 루트 실행 스크립트 수
- 중복 문서 수(유사 제목/중복 섹션)

Delivery KPI:
- PR당 변경 파일/라인
- `check-full` 통과율
- hotfix 빈도

## 6) 바로 실행 가능한 작업지시서 (첫 2주)

### Week 1

1. `scripts/repo_audit.py` 추가 및 CI artifact 생성
2. `docs/dev/` 구조 정책 SSOT 문서 확정
3. 루트 파일 분류표 작성 (유지/이관/삭제/ignore)
4. `.vscode`, `.agents`, `.githooks` 추적 범위 팀 합의

### Week 2

1. 루트 dev 유틸 스크립트 3~5개를 `scripts/devtools/`로 이동
2. 호환 shim 제공 (기존 경로 호출 시 안내/위임)
3. README 링크 정리 (중복 진입점 제거)
4. hard gate 전환 전, soft gate 경고를 CI에 게시

## 7) 리스크와 대응

- 리스크: 파일 이동으로 CI/배포 스크립트 파손
- 대응: shim + 단계적 제거 + manifest 검증 병행
- 롤백: shim 경로를 기본 경로로 재지정하고 이동 커밋을 되돌립니다.

- 리스크: 문서 정리 중 SSOT 충돌
- 대응: 정본 우선순위 표 먼저 확정 + 자동 링크 체크 유지
- 롤백: 정본 문서 외 변경을 되돌리고 링크만 유지합니다.

- 리스크: 구조 리팩토링이 운영 안전 작업을 밀어냄
- 대응: ops-safety 항목을 우선순위 상단으로 고정하고 병행 게이트 적용
- 롤백: ops-safety 미충족 변경은 merge 차단 후 구조 변경을 다음 배치로 이월합니다.

## 8) 의사결정 원칙 (Top-tier Engineer + PM)

1. 사용자 가치 역산
- 루트 정리는 미관이 아니라 onboarding 속도/실수율 개선이 목적
2. 운영 안전 우선
- 대규모 구조 변경보다 idempotency/outbox/설정 단일화 보호 우선
3. 작은 배치 + 빠른 검증
- 대형 PR 대신 연쇄형 안전 PR
4. 정책 자동화
- 사람의 기억 대신 gate/스크립트로 유지
5. 문서-코드 동기화
- SSOT 위반은 CI에서 즉시 감지

## 9) 이번 문서 개정의 실행 메모

- 본 문서는 기존 전략 문서를 "설명형"에서 "실행형 플레이북"으로 재정렬한 버전입니다.
- 특히 요청사항에 맞게 다음을 강화했습니다.
  - 루트 정리 기준의 정량화(엔트리 수/KPI)
  - 12주 로드맵의 단계별 DoD
  - 멀티 에이전트 운영 모델과 2주 작업지시서
  - dot 리소스(`.*`)의 유지/조건부/ignore 분류 원칙
- Week 2 실행 반영:
  - 루트 유틸 5개를 `scripts/devtools/`로 이관
  - 루트 호환 shim 도입(점진 제거 전략)
  - CI 빌드 경로 일부를 신규 위치로 전환
  - 루트 `README.md`를 개요/링크 중심 진입 문서로 슬림화
- Week 3 준비 반영:
  - `REPO_HYGIENE_STRICT` 토글 기반 hard gate 전환 경로를 CI/Makefile에 추가
- Week 4 실행 반영:
  - 루트 shim 9종 제거 완료 (`scripts/devtools/*` 단일 경로로 전환)
  - `pyinstaller_hooks/`를 `scripts/devtools/pyinstaller_hooks/`로 이관
- Week 5 실행 반영:
  - main CI의 repo hygiene gate 기본 모드를 `REPO_HYGIENE_STRICT=true`로 승격
  - hard gate 운영 기준을 정책/CI 가이드 문서에 동기화
- Week 6 실행 반영:
  - 루트 `env.example` 제거, `.env.example` 단일 정본으로 통합
- Week 7 실행 반영:
  - 루트 `config.example.yml`을 `config/config.example.yml`로 이관
- Week 8 실행 반영:
  - RR/Delivery Unit/Commit 범위(2~6) 거버넌스를 `pr-policy-check`에서 자동 검증
- Week 9 실행 반영:
  - 루트 `setup.cfg`, `setup.py` 제거 및 `pyproject.toml` 단일 패키징 경로 확정
- Week 10 실행 반영:
  - 루트 `.coveragerc`, `.python-version` 제거로 dot-file 표면 축소

## 10) 요청 표준(Agent/Skill + PR 중심)

- 요청 표준 문서: `docs/dev/AGENT_SKILL_REQUEST_PLAYBOOK.md`
- 구조 작업 요청 시 기본 요구사항:
  - `codex/*` 브랜치
  - 커밋/PR 단위 진행
  - `make check`, `make check-full`, `make repo-audit` 증빙
  - CI 결과 + 롤백 메모 보고
