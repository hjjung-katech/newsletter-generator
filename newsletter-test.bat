@echo off
REM Newsletter Test Command - 간단하게 CLI 테스트 명령을 실행하는 배치 파일

if "%1"=="" (
  echo Usage: newsletter-test ^<render_data_file^> [output_file]
  echo.
  echo Newsletter generation testing using existing render_data file.
  echo.
  exit /b 1
)

echo Running newsletter test with data file: %1
python -m newsletter.cli test %*
