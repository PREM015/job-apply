@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Missing .venv. Create the virtual environment before running tests. 1>&2
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python -m pytest -q
exit /b %ERRORLEVEL%
