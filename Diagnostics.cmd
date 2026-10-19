@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run Setup.cmd first.
  pause
  exit /b 1
)
echo Quit any running Quiet Quota instance from the tray menu first.
".venv\Scripts\python.exe" "%~dp0quiet_quota.py"
pause
