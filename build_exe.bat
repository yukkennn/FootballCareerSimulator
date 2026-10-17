@echo off
rem Builds the game into dist\FootballCareerSim\FootballCareerSim.exe (PyInstaller)
rem and puts a "Football Career Sim" shortcut into the project folder.
rem The whole dist\FootballCareerSim folder can be copied to another PC: Python is not needed there.
setlocal
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)
set "VPY=.venv\Scripts\python.exe"
echo Installing build tools...
"%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt pyinstaller pillow
if errorlevel 1 goto :fail
if not exist "assets\icon.ico" "%VPY%" tools\make_icon.py

echo Building FootballCareerSim.exe, 1-3 minutes...
"%VPY%" -m PyInstaller --noconfirm --clean --windowed --log-level WARN ^
  --name FootballCareerSim ^
  --icon "%CD%\assets\icon.ico" ^
  --add-data "%CD%\data;data" ^
  --add-data "%CD%\assets;assets" ^
  --distpath "%CD%\dist" --workpath "%CD%\build" --specpath "%CD%\build" ^
  --exclude-module tkinter --exclude-module unittest --exclude-module PIL ^
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtQml ^
  --exclude-module PySide6.QtQuick --exclude-module PySide6.QtPdf --exclude-module PySide6.QtMultimedia ^
  main.py
if errorlevel 1 goto :fail
rmdir /s /q build 2>nul

powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%CD%\Football Career Sim.lnk'); $s.TargetPath='%CD%\dist\FootballCareerSim\FootballCareerSim.exe'; $s.WorkingDirectory='%CD%\dist\FootballCareerSim'; $s.IconLocation='%CD%\dist\FootballCareerSim\FootballCareerSim.exe,0'; $s.Save()"

echo.
echo Done: dist\FootballCareerSim\FootballCareerSim.exe
echo Shortcut: "Football Career Sim" in the project folder.
if "%~1"=="" pause
exit /b 0
:fail
echo.
echo Build failed.
if "%~1"=="" pause
exit /b 1