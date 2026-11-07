@echo off
setlocal
cd /d "%~dp0"
if not exist "config\preferences.yaml" (
  echo NETWORK LOCK: config\preferences.yaml is required. Review the draft and create the approved file first. 1>&2
  exit /b 2
)
if not exist ".venv\Scripts\activate.bat" (
  echo Missing .venv. Create the virtual environment before running. 1>&2
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo FIXTURE - offline demonstration only; LIVE discovery is disabled.
python -m job_agent run --fixtures tests\fixtures\e2e_fixture.json --preferences config\preferences.yaml
exit /b %ERRORLEVEL%
