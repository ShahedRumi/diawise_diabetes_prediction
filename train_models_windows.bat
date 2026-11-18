@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run run_windows.bat once to install Python requirements.
  pause
  exit /b 1
)
.venv\Scripts\python.exe train_models.py
if errorlevel 1 (
  echo Training failed.
) else (
  echo Saved 3 model .pkl files inside models folder.
)
pause
