@echo off
REM r65 P4 fix: Windows equivalent of scripts/install_hooks.sh.
REM
REM Sets git config core.hooksPath to .git-hooks/ so the tracked hook
REM scripts under .git-hooks/ take effect locally. Pre-r65 only the .sh
REM version existed, requiring Windows users to run via Git Bash / MSYS2 /
REM WSL — but the project's primary dev environment is native Windows,
REM so a .bat version is the natural fit.
REM
REM Usage:
REM     scripts\install_hooks.bat

setlocal

for /f "delims=" %%i in ('git rev-parse --show-toplevel 2^>nul') do set REPO_ROOT=%%i

if "%REPO_ROOT%"=="" (
    echo [install-hooks] ERROR: not inside a git repository >&2
    exit /b 1
)

cd /d "%REPO_ROOT%"

if not exist ".git-hooks" (
    echo [install-hooks] ERROR: .git-hooks/ directory not found at %REPO_ROOT% >&2
    exit /b 1
)

git config core.hooksPath .git-hooks
if errorlevel 1 (
    echo [install-hooks] ERROR: failed to set core.hooksPath >&2
    exit /b 1
)

echo [install-hooks] core.hooksPath set to .git-hooks/
echo [install-hooks] active hooks:
for %%f in (.git-hooks\*) do (
    if /i not "%%~xf"==".md" echo   - %%~nxf
)

endlocal
