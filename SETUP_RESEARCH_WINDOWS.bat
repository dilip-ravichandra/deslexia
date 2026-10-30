@echo off
setlocal
cd /d "%~dp0"
echo DyslexiAdapt multilingual research setup - Python 3.12, CPU models.
echo Downloads pinned public model files. Several GB of disk space are required.
if not exist ".venv\Scripts\python.exe" (
 py -3.12 --version >nul 2>&1
 if errorlevel 1 (
  echo Python 3.12 is required for the pinned OCR stack. Python 3.13 cannot install it.
  echo Install Python 3.12 from python.org, then run this setup again.
  goto fail
 )
 py -3.12 -m venv .venv
 if errorlevel 1 goto fail
)
.venv\Scripts\python -c "import sys; sys.exit(0 if sys.version_info[:2] in [(3,11),(3,12)] else 1)"
if errorlevel 1 (
 echo Existing .venv uses an unsupported Python version. Create a Python 3.12 environment before continuing.
 goto fail
)
.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto fail
.venv\Scripts\python -m pip install llama-cpp-python==0.3.36 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
if errorlevel 1 goto fail
.venv\Scripts\python -m pip install -r BACKEND/requirements-research.txt
if errorlevel 1 goto fail
.venv\Scripts\python -m pip check
if errorlevel 1 goto fail
.venv\Scripts\python -m ML.multilingual_setup --vision
if errorlevel 1 goto fail
echo Setup complete. Install native Tesseract for the best tested Indic OCR:
echo winget install --id UB-Mannheim.TesseractOCR --exact --source winget
echo Then double-click START_DYSLEXIADAPT.bat.
pause
exit /b 0
:fail
echo Setup stopped because a command failed. Read the error above and RUN_RESEARCH.md.
echo No random or fake model has been substituted.
pause
exit /b 1
