@echo off
REM ----------------------------------------------------------
REM ReMD — Windows build script
REM
REM Usage:
REM   Double-click build.bat or run from Command Prompt.
REM
REM Requires Python 3.10 or later.
REM Dependencies are installed automatically.
REM ----------------------------------------------------------
cd /d "%~dp0"

REM ---- Python を探す ----
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PY=python
    goto :found
)

where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set PY=python3
    goto :found
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    set PY=py -3
    goto :found
)

echo Error: Python not found.
echo Please install Python 3.10 or later.
echo https://www.python.org/downloads/
pause
exit /b 1

:found
echo Using Python:
%PY% --version
echo.

%PY% build.py

if %errorlevel% neq 0 (
    echo.
    echo Build failed. Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo Build complete! Run dist\ReMD\ReMD.exe to start.
pause
