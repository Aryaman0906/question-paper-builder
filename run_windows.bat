@echo off
setlocal
cd /d "%~dp0"
py -3.12 main.py
if errorlevel 1 (
  echo.
  echo If Python 3.12 is unavailable, open README.md for the interpreter steps.
  pause
)
