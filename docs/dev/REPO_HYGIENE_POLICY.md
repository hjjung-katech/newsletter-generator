# Repo Hygiene Policy

이 문서는 루트 구조 정리 정책의 실행 정본(SSOT)입니다.

- 기준일: 2026-02-23
- 정책 파일: `scripts/repo_hygiene_policy.json`
- 인벤토리 도구: `scripts/repo_audit.py`
- Week 2-4 반영: 루트 유틸 이관 + 루트 shim 9종 제거 완료
- Week 5 반영: CI hard gate(`REPO_HYGIENE_STRICT=true`) 기본 활성화
- Week 10 반영: 루트 `.coveragerc`, `.python-version` 제거
- Week 11 반영: 루트 `config.yml`을 `config/config.yml`로 이관

## Scope

- 루트 엔트리 분류(유지/이관/삭제/ignore)
- dot 디렉터리(`.agents`) 추적 범위 고정 + `.vscode`/`.githooks` local-only 정책 고정
- CI repo hygiene gate 운영 기준

## Root Classification Table

다음 분류표는 Week 1~2 실행 기준입니다.

| Entry or Pattern | 결정 | 목표 위치/상태 | 근거 |
|---|---|---|---|
| `README.md`, `LICENSE`, `CHANGELOG.md`, `CODEOWNERS` | 유지 | 루트 유지 | 프로젝트 메타 |
| `pyproject.toml`, `requirements*.txt`, `Makefile` | 유지 | 루트 유지 | 빌드/패키징 |
| `setup.cfg`, `setup.py` | 제거 완료 | `pyproject.toml` 단일 경로 | 패키징 설정 중복 제거 |
| `run_ci_checks.py` | 유지 | 루트 유지 | 정책상 루트 진입 스크립트 |
| `.github/`, `.release/`, `docs/`, `scripts/`, `newsletter/`, `newsletter_core/`, `web/`, `tests/` | 유지 | 루트 유지 | 핵심 운영/도메인 디렉터리 |
| `apps/`, `config/`, `templates/` | 유지(과도기) | 루트 유지 | 현 구조 호환 유지 |
| `pyinstaller_hooks/` | 이관 완료 | `scripts/devtools/pyinstaller_hooks/` | 빌드 유틸 범주로 통합 |
| `build_web_exe.py`, `build_web_exe_enhanced.py`, `cleanup_debug_files.py`, `fix_env_setup.py`, `run_tests.py` | 삭제 완료 | `scripts/devtools/`만 사용 | 루트 clutter 제거 및 단일 실행 경로 고정 |
| `check_quality.py`, `setup_env.py`, `newsletter-test.sh`, `newsletter-test.bat` | 삭제 완료 | `scripts/devtools/`만 사용 | 루트 clutter 제거 및 단일 실행 경로 고정 |
| `.coverage`, `coverage.xml`, `coverage_html_report/` | ignore | 로컬 산출물 | 재생성 가능 산출물 |
| `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `__pycache__/` | ignore | 로컬 캐시 | 개인/런타임 캐시 |
| `output/`, `debug_files/` | ignore | 로컬 생성 디렉터리 (tracked 제외) | 실행 시 자동 생성, 루트 tracked 엔트리 축소 |
| `config/config.yml` | 유지 | `config/` 내부 정본 | 런타임 설정 파일 위치 정규화 |
| `config.example.yml` | 이관 완료 | `config/config.example.yml` | 템플릿 파일 위치 정규화 + 루트 엔트리 축소 |
| `TODOs.md` | 이관 완료 | `docs/dev/TODOs.md` | 루트 문서 혼잡도 완화 |
| 정책 미정 루트 엔트리 | 검토 | 정책 PR에서 결정 | allowlist/denylist 합의 대상 |

## Dot Directory Tracking Agreement

아래 범위만 추적합니다. 그 외 파일은 CI repo hygiene gate에서 경고/실패 처리됩니다.

### `.vscode`

- 목적: 개인 로컬 IDE 설정
- 정책: tracked 제외(local-only), 필요 시 각자 생성
- CI 처리: repo hygiene에서 ignore 대상

### `.agents`

- 목적: 장기 실행용 스킬/에이전트 정의
- 허용 추적 파일:
  - `.agents/skills/*/SKILL.md`
  - `.agents/skills/*/agents/openai.yaml`
- 금지: 실행 로그/캐시/개인 실험 산출물

### `.githooks`

- 목적: 개인 로컬 hooksPath 실험용 디렉터리
- 정책: tracked 제외(local-only), 필요 시 각자 생성
- CI 처리: repo hygiene에서 ignore 대상

### Hook Source (Tracked)

- pre-push 훅 원본 경로: `scripts/devtools/hooks/pre-push`
- 로컬 설치 스크립트: `scripts/devtools/setup_pre_push_hook.sh`

## CI Repo Hygiene Gate

- 위치: `.github/workflows/main-ci.yml`의 `quality-checks` stage
- 실행 명령:
  - `python scripts/repo_audit.py --policy scripts/repo_hygiene_policy.json --output-dir artifacts/repo-audit --check-policy`
- strict 토글:
  - `REPO_HYGIENE_STRICT=true`(기본): `--strict` 활성화, warning 발견 시 CI 실패(hard gate)
  - `REPO_HYGIENE_STRICT=false`: 임시 soft gate override(경고만 출력)
- 산출물(artifact):
  - `artifacts/repo-audit/repo_audit_report.md`
  - `artifacts/repo-audit/repo_audit_report.json`
  - `artifacts/repo-audit/policy_warnings.md`
- 운영 원칙:
  - Week 1~4: warning-only soft gate로 준비 단계 운영
  - Week 5+: hard gate 기본 운영, 예외 시에만 일시 override 검토

### Shim Policy (Week 4)

- 루트 shim은 더 이상 유지하지 않습니다.
- 실행/유틸 스크립트 경로는 `scripts/devtools/*`로 단일화합니다.
- soft/strict 모드 모두 루트 shim 파일 생성을 허용하지 않습니다.

## Local Runbook

```bash
python scripts/repo_audit.py \
  --policy scripts/repo_hygiene_policy.json \
  --output-dir artifacts/repo-audit \
  --check-policy
```

strict 모드(CI 기본):

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

- 본 문서는 Week 1 기준선에서 현재 운영 상태로 지속 업데이트합니다.
- 정책 변경은 반드시 PR로 수행하고, `scripts/repo_hygiene_policy.json`과 함께 변경합니다.
- root 예외 추가 시 사유와 제거 목표 시점을 PR 설명에 명시합니다.
