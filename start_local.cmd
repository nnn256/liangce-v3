@echo off
setlocal
cd /d "%~dp0"
title Liangce v3 - Local Chanlun Research
if not exist ".venv\Scripts\python.exe" (
  echo Missing local Python environment: .venv\Scripts\python.exe
  echo Please run this launcher from D:\stock-dashboard.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" run_local.py %*
if errorlevel 1 pause
endlocal
