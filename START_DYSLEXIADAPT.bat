@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo First-time setup is needed. Open RUN_RESEARCH.md and follow the three setup commands.
 pause
 exit /b 1
)
.venv\Scripts\python.exe launch_interface.py
pause
