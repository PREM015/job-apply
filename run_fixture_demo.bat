@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Missing .venv. Create the virtual environment before running the fixture demo. 1>&2
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo FIXTURE - offline sample jobs only; not real jobs.
python -m job_agent --db data\fixture_job_agent.sqlite3 run --fixtures tests\fixtures\e2e_fixture.json --preferences config\preferences.example.yaml
if errorlevel 1 exit /b %ERRORLEVEL%
if not exist data\exports mkdir data\exports
python -m job_agent --db data\fixture_job_agent.sqlite3 export --out data\exports\fixture_queue.xlsx
exit /b %ERRORLEVEL%
