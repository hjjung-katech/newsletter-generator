# Devtools Scripts

이 디렉터리는 루트에서 이관된 개발/운영 유틸 스크립트의 정식 위치입니다.

## Migrated in Week 2

- `build_web_exe.py`
- `build_web_exe_enhanced.py`
- `cleanup_debug_files.py`
- `fix_env_setup.py`
- `run_tests.py`
- `check_quality.py`
- `setup_env.py`
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
