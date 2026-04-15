# Lessons

## 2026-04-15 Prompt A~B 시리즈 교훈

### 의존성 관리
- lock 파일 없이 lower bound 현실화 불가
  → 작업 전 반드시 pip freeze 선행
  → venv 위치가 비표준(.local/venv/)일 수 있으므로 탐색 단계 필요

### repo hygiene policy
- 루트에 신규 파일 추가 시 scripts/repo_hygiene_policy.json
  allowlist 동시 수정 필요
  → 미리 확인하지 않으면 CI Code Quality gate 실패

### 에이전트 범위 제어
- "별도 PR로 남겨둔다" 지시만으로는 불충분
  → git add -p 로 명시적으로 staging 범위 강제해야 함
  → 에이전트가 범위 외 변경사항을 조용히 포함할 수 있음

### 프롬프트 설계
- Read → Verify → Write 순서 강제 필수
  → 각 step에 print 강제 없으면 에이전트가 건너뜀
- stop 조건을 명시적으로 설계해야 함
  → 조건 불충족 시 에이전트가 guessing으로 진행할 수 있음

## LESSON-001: 별도 PR 지시는 staging 레벨에서 강제해야 한다

### 발생 시점
PR #434 (docs/readme-operator-positioning)

### 무슨 일이 있었나
- 지시: "L54, L112, Use Cases 섹션은 별도 PR로 남긴다"
- 실제: 에이전트가 해당 라인까지 같이 수정해서 동일 PR에 포함
- CI는 통과했고 결과물은 올바르지만 지시한 범위를 초과

### 근본 원인
- "별도 PR로 남긴다"는 지시가 텍스트 레벨에만 존재
- 에이전트가 diff 생성 시 해당 라인을 제외할 강제 수단 없음

### 올바른 지시 패턴
범위를 제한할 때는 반드시 git 레벨에서 강제한다:

  # 나쁜 예 (텍스트 지시만)
  "L54, L112는 이번 PR에 포함하지 마라"

  # 좋은 예 (git 레벨 강제)
  "git add -p 로 L54, L112, Use Cases 섹션을
   staging에서 제외한 뒤 git diff --cached 로
   확인하고 나서 commit 해라"

### 적용 범위
파일 일부만 커밋해야 하는 모든 작업에 적용.
특히 큰 파일(README.md, routes_generation.py 등)의
부분 수정 시 필수.
