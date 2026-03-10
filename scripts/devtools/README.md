# Devtools Scripts

이 디렉터리는 루트에서 이관된 개발/운영 유틸 스크립트의 정식 위치입니다.

## Canonical Contributor Entrypoint

- `python -m scripts.devtools.dev_entrypoint`
- `bootstrap`, `doctor`, `check`, `check --full`, `run`, `smoke` 같은 contributor-facing 공통 명령은 이 엔트리포인트를 기준으로 유지합니다.
- `Makefile`과 shell hook은 backward-compatible wrapper로만 유지합니다.

## Migrated in Week 2

- `build_web_exe.py` (compatibility shim)
- `build_web_exe_enhanced.py` (canonical)
- `cleanup_debug_files.py`
- `fix_env_setup.py`
- `run_tests.py`
- `check_quality.py`
- `setup_env.py`
- `generate_windows_release_artifacts.py`
- `verify_windows_artifact_checksum.py`
- `create_support_bundle.py`
- `windows_exe_smoke.ps1`
- `sign_windows_exe.ps1`
- `validate_windows_release_artifacts.py`
- `generate_windows_update_manifest.py`
- `windows_ci_burnin_report.py`
- `check_legacy_web_types_paths.py`
- `newsletter-test.sh`
- `newsletter-test.bat`

## Process Helpers

- `setup_git_message_template.sh`
  - 로컬 Git commit 템플릿을 `.gitmessage.txt`로 설정합니다.
  - 실행: `./scripts/devtools/setup_git_message_template.sh`
- `setup_pre_push_hook.sh`
  - 로컬 `.git/hooks/pre-push`에 표준 pre-push 가드를 설치합니다.
  - 실행: `./scripts/devtools/setup_pre_push_hook.sh`

## Hooks

- `hooks/pre-push`
  - 표준 pre-push 훅 원본입니다.
  - 설치는 `setup_pre_push_hook.sh` 또는 `make pre-push-hook`으로 수행합니다.

## Backward Compatibility

- 루트 동일 파일명은 현재 shim으로 유지됩니다.
- shim은 실행 시 `scripts/devtools/*`로 위임하고 deprecation 메시지를 출력합니다.
- shim 제거는 Phase 2 후반(호환 기간 종료)에서 진행합니다.
