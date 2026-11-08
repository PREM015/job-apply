@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Missing .venv. Create the virtual environment before running the fixture demo. 1>&2
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo FIXTURE - offline sample jobs only; not real jobs.
python -m job_agent fixture-demo
exit /b %ERRORLEVEL%
