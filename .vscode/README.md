# VS Code 개발 환경 설정

이 폴더는 Visual Studio Code 편집기를 위한 프로젝트 설정 파일을 포함하고 있습니다.
모든 팀원이 동일한 개발 환경을 쉽게 구성할 수 있도록 도와줍니다.

## 포함된 설정 파일

### settings.json

- Python 인터프리터 경로 설정
- 가상환경 자동 활성화
- 테스트 프레임워크 설정 (pytest)
- 코드 형식화 도구 설정 (black)

### launch.json

- 디버깅 구성 정의
- 테스트 실행 구성:
  - 모든 테스트 실행
  - 특정 테스트 실행
  - 테스트 목록 표시
- 모듈 실행 구성

### tasks.json

- 코드 포맷팅 작업
- 테스트 실행 작업
- 가상환경 활성화 작업
- 개발 의존성 설치 작업

### extensions.json

- 프로젝트에 권장되는 VS Code 확장 프로그램 목록

## 커스터마이징

각 개발자의 로컬 환경에 맞게 설정을 변경해야 할 경우:

1. **가상환경 경로 변경**:
   - `settings.json`의 `python.defaultInterpreterPath` 값을 수정
   - 기본값: `${workspaceFolder}/.venv/Scripts/python.exe`

2. **Conda 환경 이름 변경**:
   - `settings.json`의 `terminal.integrated.profiles.windows.args` 값에서
     `conda activate newsletter-env` 부분을 원하는 환경 이름으로 변경

3. **테스트 경로 변경**:
   - `settings.json`의 `python.testing.pytestArgs` 배열 수정
   - 기본값: `["tests"]`

## 주의사항

이 설정은 Windows 환경을 기준으로 작성되었습니다. 다른 OS를 사용하는 경우:

- Linux/macOS: `settings.json`의 경로 구분자를 `/`로 수정
- 터미널 프로필: OS에 맞는 프로필 구성 필요 (Linux/macOS: `terminal.integrated.profiles.osx` 또는 `terminal.integrated.profiles.linux`)
