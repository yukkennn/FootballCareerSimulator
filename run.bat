@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment, first start only...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :fail
exit /b 0
:fail
echo.
echo Something went wrong. Install Python 3.10+ from https://www.python.org/downloads/ and tick "Add Python to PATH".
pause
exit /b 1
