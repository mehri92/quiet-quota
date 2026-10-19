@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.10 or newer from python.org, including the Python Launcher.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo.
echo Setup complete. Run Demo.cmd to test the popup, or Start.cmd for live usage.
echo Live mode needs the Windows Codex CLI signed in with ChatGPT.
pause
exit /b 0
:fail
echo Setup failed. See the error above.
pause
exit /b 1
