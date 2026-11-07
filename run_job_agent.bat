@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if "%~1"=="" (
  echo Usage: run_job_agent.bat ^<command^> [args] 1>&2
  echo Example: run_job_agent.bat run --fixtures tests\fixtures\e2e_fixture.json --preferences config\preferences.example.yaml 1>&2
  exit /b 2
)

if not exist logs mkdir logs
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

echo [%date% %time%] starting: %*>> logs\scheduler.log
"%PYTHON%" -m job_agent --config config\config.yaml %* >> logs\scheduler.log 2>&1
set "RC=!ERRORLEVEL!"
echo [%date% %time%] exit=!RC! >> logs\scheduler.log
exit /b !RC!
