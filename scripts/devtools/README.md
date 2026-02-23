# Devtools Scripts

이 디렉터리는 루트에서 이관된 개발/운영 유틸 스크립트의 정식 위치입니다.

## Migrated in Week 2

- `build_web_exe.py`
- `build_web_exe_enhanced.py`
- `cleanup_debug_files.py`
- `fix_env_setup.py`
- `run_tests.py`

## Backward Compatibility

- 루트 동일 파일명은 현재 shim으로 유지됩니다.
- shim은 실행 시 `scripts/devtools/*`로 위임하고 deprecation 메시지를 출력합니다.
- shim 제거는 Phase 2 후반(호환 기간 종료)에서 진행합니다.
