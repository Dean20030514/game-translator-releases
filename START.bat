@echo off
setlocal

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10+ is required but not found in PATH.
    echo         See https://www.python.org/downloads/ for installation.
    pause
    exit /b 1
)

REM r64 S3 fix: validate Python >= 3.10 (PEP 604 union syntax requirement,
REM see ADR 0006). Pre-r64 START.bat only checked existence; users with
REM Python 3.9 would hit cryptic PEP 604 TypeErrors at runtime.
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10+ is required.
    echo         Detected version is below 3.10.
    python --version
    echo         See ADR 0006 (Python 3.10 floor) — PEP 604 union syntax requires 3.10+.
    pause
    exit /b 1
)

python "%~dp0start_launcher.py"
set CODE=%ERRORLEVEL%

echo.
echo Exit code: %CODE%
pause
exit /b %CODE%
