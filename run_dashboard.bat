@echo off
setlocal
cd /d "%~dp0"

if not exist logs mkdir logs
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

"%PYTHON%" -m streamlit run job_agent\dashboard\app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false --server.fileWatcherType none
exit /b %ERRORLEVEL%
