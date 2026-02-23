@echo off
REM Compatibility shim for legacy root script path.

set "TARGET=%~dp0scripts\devtools\newsletter-test.bat"

if not exist "%TARGET%" (
  echo [shim-error] Missing target script: %TARGET% 1>&2
  exit /b 2
)

echo [deprecated] newsletter-test.bat moved to scripts/devtools/newsletter-test.bat 1>&2
call "%TARGET%" %*
exit /b %errorlevel%
