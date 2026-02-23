# Repo Hygiene Policy (Week 1-2 Baseline)

이 문서는 루트 구조 정리 정책의 실행 정본(SSOT)입니다.

- 기준일: 2026-02-23
- 정책 파일: `scripts/repo_hygiene_policy.json`
- 인벤토리 도구: `scripts/repo_audit.py`
- Week 2-4 반영: 루트 유틸 이관 + 루트 shim 9종 제거 완료

## Scope

- 루트 엔트리 분류(유지/이관/삭제/ignore)
- dot 디렉터리(`.vscode`, `.agents`, `.githooks`) 추적 범위 고정
- CI soft gate(warning-only) 운영 기준

## Root Classification Table

다음 분류표는 Week 1~2 실행 기준입니다.

| Entry or Pattern | 결정 | 목표 위치/상태 | 근거 |
|---|---|---|---|
| `README.md`, `LICENSE`, `CHANGELOG.md`, `CODEOWNERS` | 유지 | 루트 유지 | 프로젝트 메타 |
| `pyproject.toml`, `requirements*.txt`, `Makefile`, `setup.cfg`, `setup.py` | 유지 | 루트 유지 | 빌드/패키징 |
| `run_ci_checks.py` | 유지 | 루트 유지 | 정책상 루트 진입 스크립트 |
| `.github/`, `.release/`, `docs/`, `scripts/`, `newsletter/`, `newsletter_core/`, `web/`, `tests/` | 유지 | 루트 유지 | 핵심 운영/도메인 디렉터리 |
| `apps/`, `config/`, `packages/`, `pyinstaller_hooks/`, `templates/` | 유지(과도기) | 루트 유지 | 현 구조 호환 유지 |
| `build_web_exe.py`, `build_web_exe_enhanced.py`, `cleanup_debug_files.py`, `fix_env_setup.py`, `run_tests.py` | 삭제 완료 | `scripts/devtools/`만 사용 | 루트 clutter 제거 및 단일 실행 경로 고정 |
| `check_quality.py`, `setup_env.py`, `newsletter-test.sh`, `newsletter-test.bat` | 삭제 완료 | `scripts/devtools/`만 사용 | 루트 clutter 제거 및 단일 실행 경로 고정 |
| `.coverage`, `coverage.xml`, `coverage_html_report/` | ignore | 로컬 산출물 | 재생성 가능 산출물 |
| `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `__pycache__/` | ignore | 로컬 캐시 | 개인/런타임 캐시 |
| `output/`, `debug_files/` | 유지(가드 포함) | `.gitkeep`만 추적 + 생성물 ignore | 실행 중 생성 경로 필요 |
| `.coveragerc`, `config.yml` | 유지 | 루트 allowlist | 런타임/테스트 기본 설정 경로 호환 |
| `TODOs.md` | 이관 완료 | `docs/dev/TODOs.md` | 루트 문서 혼잡도 완화 |
| 정책 미정 루트 엔트리 | 검토 | 정책 PR에서 결정 | allowlist/denylist 합의 대상 |

## Dot Directory Tracking Agreement

아래 범위만 추적합니다. 그 외 파일은 CI soft gate에서 경고합니다.

### `.vscode`

- 목적: 팀 공통 개발 경험 공유
- 허용 추적 파일:
  - `.vscode/README.md`
  - `.vscode/settings.json`
  - `.vscode/tasks.json`
  - `.vscode/extensions.json`
  - `.vscode/launch.json`
- 금지: 개인 편의/로컬 경로 의존 설정

### `.agents`

- 목적: 장기 실행용 스킬/에이전트 정의
- 허용 추적 파일:
  - `.agents/skills/*/SKILL.md`
  - `.agents/skills/*/agents/openai.yaml`
- 금지: 실행 로그/캐시/개인 실험 산출물

### `.githooks`

- 목적: 공통 pre-push 가드
- 허용 추적 파일:
  - `.githooks/pre-push`
- 금지: 개인 훅/로컬 자동생성 스크립트

## CI Soft Gate

- 위치: `.github/workflows/main-ci.yml`의 `quality-checks` stage
- 실행 명령:
  - `python scripts/repo_audit.py --policy scripts/repo_hygiene_policy.json --output-dir artifacts/repo-audit --check-policy`
- strict 전환 준비 토글:
  - `REPO_HYGIENE_STRICT=false`(기본): warning-only soft gate
  - `REPO_HYGIENE_STRICT=true`: `--strict`가 활성화되어 warning 발견 시 CI 실패
- 산출물(artifact):
  - `artifacts/repo-audit/repo_audit_report.md`
  - `artifacts/repo-audit/repo_audit_report.json`
  - `artifacts/repo-audit/policy_warnings.md`
- 운영 원칙:
  - Week 1~2: warning-only(실패로 승격하지 않음)
  - Phase 3: hard gate 전환 검토

### Shim Policy (Week 4)

- 루트 shim은 더 이상 유지하지 않습니다.
- 실행/유틸 스크립트 경로는 `scripts/devtools/*`로 단일화합니다.
- soft/strict gate 모두 루트 shim 파일 생성을 허용하지 않습니다.

## Local Runbook

```bash
python scripts/repo_audit.py \
  --policy scripts/repo_hygiene_policy.json \
  --output-dir artifacts/repo-audit \
  --check-policy
```

strict 모드(향후 hard gate용):

```bash
python scripts/repo_audit.py \
  --policy scripts/repo_hygiene_policy.json \
  --output-dir artifacts/repo-audit \
  --check-policy \
  --strict
```

Makefile 단축 명령:

```bash
make repo-audit
make repo-audit-strict
```

## Governance Notes

- 본 문서는 Week 1~2 기준선입니다.
- 정책 변경은 반드시 PR로 수행하고, `scripts/repo_hygiene_policy.json`과 함께 변경합니다.
- root 예외 추가 시 사유와 제거 목표 시점을 PR 설명에 명시합니다.
