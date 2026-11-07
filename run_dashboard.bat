@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo Missing .venv. Create the virtual environment before starting the dashboard. 1>&2
  exit /b 1
)
call ".venv\Scripts\activate.bat"

python -m streamlit run job_agent\dashboard\app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false --server.fileWatcherType none
exit /b %ERRORLEVEL%
