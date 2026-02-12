@echo off
REM ----------------------------------------------------------
REM ReMD — Windows build script
REM
REM Usage:
REM   build.bat をダブルクリック、または コマンドプロンプトで実行
REM
REM Python 3.10 以上が必要です。
REM 依存パッケージは自動でインストールされます。
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

echo Error: Python が見つかりません。
echo Python 3.10 以上をインストールしてください。
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
    echo ビルドに失敗しました。上のエラーメッセージを確認してください。
    pause
    exit /b 1
)

echo.
echo ビルド完了！ dist\ReMD\ReMD.exe を実行してください。
pause
