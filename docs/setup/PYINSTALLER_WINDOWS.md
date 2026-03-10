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
python -m venv .local\venv
.\.local\venv\Scripts\activate

# 필요한 패키지 설치
pip install -r requirements.txt
pip install pyinstaller
```

## 3. 실행 파일 생성 (Canonical)

```powershell
# Canonical 빌드 스크립트 실행
python scripts/devtools/build_web_exe_enhanced.py
```

완료되면 `dist\newsletter_web.exe` 파일이 생성됩니다. 이 파일은 Python 환경 없이 바로 실행할 수 있습니다.

> 참고: `python scripts/devtools/build_web_exe.py`는 호환용 shim이며 내부적으로 `build_web_exe_enhanced.py`를 호출합니다.
> 타입 로딩 기준은 `web.types`가 canonical이며, `web.web_types`/`web_types`는 런타임 호환 alias로만 유지됩니다.

## 4. 실행 및 데이터베이스 초기화

생성된 `newsletter_web.exe` 를 실행하면 같은 폴더에 `storage.db` 파일이 생성되며, 웹 서버가 기본 포트 5000에서 시작됩니다.

```powershell
./dist/newsletter_web.exe
# 브라우저에서 http://localhost:5000 접속
```

## 5. 릴리즈 메타데이터/무결성 생성

```powershell
python scripts/devtools/generate_windows_release_artifacts.py --artifact dist/newsletter_web.exe --output-dir dist --target-os windows-x64
python scripts/devtools/create_support_bundle.py --artifact dist/newsletter_web.exe --dist-dir dist --checksum-file dist/SHA256SUMS.txt --output dist/support-bundle.zip
python scripts/devtools/generate_windows_update_manifest.py --metadata dist/release-metadata.json --output dist/update-manifest.json --base-url "https://download.example.com/newsletter/windows" --checksum-file dist/SHA256SUMS.txt
python scripts/devtools/verify_windows_artifact_checksum.py --artifact dist/newsletter_web.exe --artifact dist/release-metadata.json --artifact dist/support-bundle.zip --artifact dist/update-manifest.json --checksum-file dist/SHA256SUMS.txt
python scripts/devtools/validate_windows_release_artifacts.py --dist-dir dist
python scripts/devtools/check_legacy_web_types_paths.py
```

- `dist\release-metadata.json`: 버전/빌드시각/Git SHA/Smoke 결과 등 릴리즈 메타데이터
- `dist\SHA256SUMS.txt`: `newsletter_web.exe`, `release-metadata.json`, `support-bundle.zip`, `update-manifest.json` 무결성 체크섬
- `dist\support-bundle.zip`: 지원/장애 재현용 마스킹 진단 번들(`bundle-manifest.json`, `recent-errors.txt` 포함)

## 6. 배포

생성된 `newsletter_web.exe` 단일 파일만 전달하면 됩니다. 필요 시 `dist` 폴더를 압축하여 배포할 수 있습니다.

운영 정책(코드서명/업데이트/SLA/롤백)은 `docs/setup/WINDOWS_EXE_OPERATIONS.md`를 따릅니다.
Smoke 대응 절차는 `docs/setup/WINDOWS_EXE_SMOKE_PLAYBOOK.md`를 따릅니다.
업데이트 채널 운영은 `docs/setup/WINDOWS_EXE_UPDATE_CHANNEL.md`를 따릅니다.
