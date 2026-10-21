@echo off
setlocal
cd /d "%~dp0"
python tools\import_jun.py
if errorlevel 1 (
  echo.
  echo Import stopped. See the message above; your saves are unchanged.
  pause
  exit /b 1
)
pause
