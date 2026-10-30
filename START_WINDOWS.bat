@echo off
setlocal
cd /d "%~dp0"
echo DyslexiAdapt multilingual reader

if not exist ".venv\Scripts\python.exe" goto setup
".venv\Scripts\python.exe" -c "from ML.readiness import services; s=services(); raise SystemExit(0 if s['supported_research_python'] and all(s[name]['ready'] for name in ('local_accounts','generation','routing_backbone','vision','semantic_checks')) and all(v['ready'] for v in s['speech'].values()) else 1)"
if errorlevel 1 goto setup
goto launch

:setup
echo Current multilingual models or dependencies need setup.
call "%~dp0SETUP_RESEARCH_WINDOWS.bat"
if errorlevel 1 exit /b 1

:launch
echo Sign in or create a profile: http://127.0.0.1:8000/account.html
echo Reader: http://127.0.0.1:8000
echo Research lab: http://127.0.0.1:8000/research-demo.html
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" launch_interface.py
if errorlevel 1 (
 pause
 exit /b 1
)
exit /b 0
