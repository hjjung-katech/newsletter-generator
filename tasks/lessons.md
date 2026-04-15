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

## LESSON-002: test/ 브랜치 prefix 는 CI 에서 허용되지 않는다

### 발생 시점
PR 계획 단계 (2026-04-15, 브랜치 생성 전 prefix 점검 과정에서 식별)

### 무슨 일이 있었나
- 브랜치명에 test/ prefix 사용 시도
- CI branch-name policy 가 허용 prefix 를 `feat|fix|chore|docs|refactor|release|codex` 로
  제한하며, test/ 는 이 목록에 포함되지 않음
- 결과: CI branch-name gate 실패

### 근본 원인
- CLAUDE.md Workflow Contract 에 허용 prefix 목록이 명시되어 있으나
  브랜치 생성 전 확인하지 않음
- test/ 는 직관적으로 허용될 것처럼 보이나 실제로는 chore/ 로 대체해야 함

### 올바른 지시 패턴
브랜치 생성 전 항상 허용 prefix 목록 확인:

  # 허용 목록 (CLAUDE.md Workflow Contract)
  feat | fix | chore | docs | refactor | release | codex

  # 나쁜 예
  git checkout -b test/my-feature

  # 좋은 예
  git checkout -b chore/my-feature

### 적용 범위
모든 브랜치 생성 시 적용. 특히 테스트 관련 작업은 chore/ 사용.

## LESSON-003: 신규 디렉토리 추가 시 __init__.py 를 즉시 추가해야 한다

### 발생 시점
PR 계획 단계 (2026-04-15, Step 6 pre-write checklist 항목으로 식별)

### 무슨 일이 있었나
- Python 패키지 디렉토리를 신규 생성했으나 __init__.py 누락
- 해당 디렉토리가 implicit namespace package 로 처리되어
  다른 패키지와 namespace 충돌 또는 import 오류 발생

### 근본 원인
- Python 3 의 implicit namespace package 기능으로 인해
  __init__.py 없이도 디렉토리가 패키지처럼 동작
- 그러나 기존 패키지와 동일 namespace 를 공유할 경우 예측 불가한 import 충돌

### 올바른 지시 패턴
신규 디렉토리 생성 직후 __init__.py 를 함께 추가:

  # 나쁜 예
  mkdir newsletter_core/new_module/
  # __init__.py 없이 진행

  # 좋은 예
  mkdir newsletter_core/new_module/
  touch newsletter_core/new_module/__init__.py

### 적용 범위
newsletter_core/, newsletter/, web/ 하위 모든 신규 디렉토리 추가 시 필수.

## LESSON-004: ci 커밋 타입은 허용 목록에 없다 — chore 를 사용한다

### 발생 시점
PR #448 (chore/p1-c-shell-size-soft-gate), 2026-04-15

### 무슨 일이 있었나
- GitHub Actions 워크플로우 파일 추가 커밋에 `ci(size-gate):` 타입 사용
- pr-policy-check.yml 이 허용 커밋 타입을 `feat|fix|chore|docs|refactor|release|codex` 로
  제한하며, ci 는 이 목록에 포함되지 않음
- 결과: policy-check CI gate 실패 → 커밋을 `chore(size-gate):` 로 amend 후 force-push

### 근본 원인
- CLAUDE.md Workflow Contract 에 허용 타입 목록이 명시되어 있으나
  커밋 작성 전 확인하지 않음
- ci 는 Conventional Commits 표준에는 존재하지만 이 저장소 정책에서는 금지

### 올바른 지시 패턴
커밋 작성 전 항상 허용 타입 목록 확인:

  # 허용 목록 (CLAUDE.md Workflow Contract / pr-policy-check.yml)
  feat | fix | chore | docs | refactor | release | codex

  # 나쁜 예
  ci(size-gate): add freeze module size gate workflow

  # 좋은 예
  chore(size-gate): add freeze module size gate workflow

### 적용 범위
모든 커밋 타입 선택 시 적용. CI 관련 변경(워크플로우, 스크립트)은 chore 사용.

## LESSON-005: CI mypy 는 --follow-imports=skip 모드로 실행되어 local 과 동작 차이 발생

### 발생 시점
PR #450 (chore/p1-b-mypy-public-enable), 2026-04-15

### 무슨 일이 있었나
- local `mypy newsletter_core/public/` → 0 errors
- CI `mypy --ignore-missing-imports --follow-imports=skip <file>` → 2 errors
  - `[untyped-decorator]`: `@tool` decorator (langchain)가 skip 모드에서 Any 처리
  - `[no-any-return]`: 같은 패키지 내 함수의 반환 타입이 skip으로 Any 처리
- `# type: ignore` 방식은 `warn_unused_ignores = true` 충돌
  (로컬에서는 ignore가 unused, CI에서는 used → 서로 다른 환경에서 반대 에러)

### 근본 원인
- CI mypy가 파일별로 `--follow-imports=skip` 실행 (main-ci.yml 참조)
- skip 모드에서는 같은 패키지 내 모듈 import도 `Any`로 처리
- `warn_unused_ignores = true`와 조합 시 inline `# type: ignore` 방식은 환경간 충돌

### 올바른 지시 패턴
CI mypy 동작을 local에서 재현한 후 수정:

  # CI mypy 재현
  python -m mypy --ignore-missing-imports --follow-imports=skip <파일>

  # 수정 방법 (우선순위):
  # 1. 타입이 명시된 중간 변수로 반환 타입 확정 (# type: ignore 불필요)
  filtered: List[Dict[str, Any]] = some_func(args)
  return filtered

  # 2. pyproject.toml override 로 특정 check 비활성화 (모듈 전체 억제)
  # [[tool.mypy.overrides]]
  # module = ["newsletter_core.public.*"]
  # disallow_untyped_decorators = false  # @tool 등 외부 라이브러리 데코레이터

  # 피해야 할 패턴:
  return some_func(args)  # type: ignore[no-any-return]
  # → local에서 unused ignore 에러 발생

### 적용 범위
CI mypy 오류 수정 시 항상 `--follow-imports=skip` 모드 재현 후 수정.
inline # type: ignore 대신 중간 변수 또는 pyproject.toml override 우선 사용.

## LESSON-006: pytest-playwright 대신 playwright 단독 사용 — pytest-base-url scope 충돌 회피

### 발생 시점
PR #454 (chore/p1-d-e2e-playwright-smoke), 2026-04-15

### 무슨 일이 있었나
- `pytest-playwright` 설치 시 `pytest-base-url`이 자동 설치됨
- `pytest-base-url`이 session-scoped `_verify_url` autouse fixture를 등록,
  이 fixture가 `base_url`을 요청
- `tests/conftest.py`의 `base_url`이 function-scoped이므로 ScopeMismatch 발생
- 기존 테스트 전체에 영향 (e2e 외 테스트도 실패)

### 근본 원인
- `pytest-playwright`의 transitive 의존성인 `pytest-base-url`이 global autouse fixture를 등록
- 기존 `base_url` fixture (function scope)와 충돌

### 올바른 지시 패턴
`pytest-playwright` 대신 `playwright` 단독 패키지를 사용하고
`browser`, `page` fixture를 `tests/e2e/conftest.py`에 직접 구현:

  # 나쁜 예
  # pyproject.toml: pytest-playwright>=0.4.0
  # tests/e2e/test_smoke.py: from playwright.sync_api import Page  # pytest-playwright가 제공

  # 좋은 예
  # pyproject.toml: playwright>=1.40.0 (e2e extras group)
  # tests/e2e/conftest.py: browser/page fixture 직접 구현
  @pytest.fixture(scope="session")
  def browser():
      with sync_playwright() as pw:
          yield pw.chromium.launch(headless=True, args=["--no-sandbox"])

### 적용 범위
Playwright E2E 테스트 추가 시 항상 `playwright` 단독 사용.
`pytest-playwright` 사용 시 반드시 tests/conftest.py의 base_url scope 충돌 여부 사전 확인.

## LESSON-007: e2e CI job은 requirements.txt 설치 방식 사용 — pyproject.toml extras 불충분

### 발생 시점
PR #454 (chore/p1-d-e2e-playwright-smoke), 2026-04-15

### 무슨 일이 있었나
- `pip install -e ".[dev,e2e]"` 로 설치 시 `flask-cors` 누락
- `flask-cors`는 `requirements.txt`에만 존재하고 `pyproject.toml` 의존성에 없음
- e2e-smoke CI에서 `ModuleNotFoundError: No module named 'flask_cors'` 발생

### 근본 원인
- 이 저장소는 `requirements.txt` + `requirements-dev.txt` 방식과
  `pyproject.toml` 방식이 동시에 존재 (혼용 구조)
- web runtime 의존성(`flask-cors` 등)은 `requirements.txt`에만 있음

### 올바른 지시 패턴
이 저장소의 CI job은 `pip install -r requirements.txt` + `pip install -r requirements-dev.txt` 방식을 사용:

  # 나쁜 예
  pip install -e ".[dev,e2e]"  # flask-cors 등 web runtime 의존성 누락

  # 좋은 예 (main-ci.yml 동일 패턴)
  pip install -r requirements.txt
  pip install -r requirements-dev.txt
  pip install playwright  # e2e 전용 추가 패키지

### 적용 범위
이 저장소에서 새 CI job 추가 시 의존성 설치는 반드시 main-ci.yml 방식을 참조.
