# Windows PyInstaller 빌드 가이드

이 문서는 Flask 기반 웹 서버를 Windows 환경에서 단일 실행 파일(`.exe`)로 패키징하는 방법을 설명합니다.

## 1. 준비 사항

- Windows 10/11
- Python 3.12 이상 설치
- Git 설치 (선택 사항)

## 2. 저장소 클론 및 의존성 설치

```powershell
# 저장소 클론
git clone https://github.com/hjjung-katech/newsletter-generator.git
cd newsletter-generator

# 가상환경 생성 및 활성화
python -m venv .venv
.\.venv\Scripts\activate

# 필요한 패키지 설치
pip install -r requirements.txt
pip install pyinstaller
```

## 3. 실행 파일 생성

```powershell
# PyInstaller 스크립트 실행
python build_web_exe.py
```

완료되면 `dist\newsletter_web.exe` 파일이 생성됩니다. 이 파일은 Python 환경 없이 바로 실행할 수 있습니다.

## 4. 실행 및 데이터베이스 초기화

생성된 `newsletter_web.exe` 를 실행하면 같은 폴더에 `storage.db` 파일이 생성되며, 웹 서버가 기본 포트 5000에서 시작됩니다.

```powershell
./dist/newsletter_web.exe
# 브라우저에서 http://localhost:5000 접속
```

## 5. 배포

생성된 `newsletter_web.exe` 단일 파일만 전달하면 됩니다. 필요 시 `dist` 폴더를 압축하여 배포할 수 있습니다.
