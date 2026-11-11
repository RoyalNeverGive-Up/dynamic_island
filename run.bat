@echo off
setlocal
title Dynamic Island Launcher
cd /d "%~dp0"

:: 1. Fast path: check if local virtual environment already exists
if exist "%~dp0.venv\Scripts\python.exe" (
    goto :check_and_launch
)

:: 2. Find a valid native Windows Python interpreter (prefer 3.9 ~ 3.13)
set "PY_CMD="

:: Strategy A: Check 'py -3' (Python Launcher for Windows)
py -3 -c "import sys; exit(0 if (3, 9) <= sys.version_info[:2] <= (3, 13) and 'msys' not in sys.executable.lower() and 'mingw' not in sys.executable.lower() else 1)" >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto :init_venv
)

:: Strategy B: Scan AppData programs
for %%v in (313 312 311 310 39) do (
    if not defined PY_CMD (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" (
            "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" -c "import sys; exit(0 if (3, 9) <= sys.version_info[:2] <= (3, 13) else 1)" >nul 2>nul
            if not errorlevel 1 set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
        )
    )
)
if defined PY_CMD goto :init_venv

:: Strategy C: Scan Program Files
for %%v in (313 312 311 310 39) do (
    if not defined PY_CMD (
        if exist "%ProgramFiles%\Python%%v\python.exe" (
            "%ProgramFiles%\Python%%v\python.exe" -c "import sys; exit(0 if (3, 9) <= sys.version_info[:2] <= (3, 13) else 1)" >nul 2>nul
            if not errorlevel 1 set "PY_CMD=%ProgramFiles%\Python%%v\python.exe"
        )
    )
)
if defined PY_CMD goto :init_venv

:: Strategy D: Check 'python' in PATH (exclude MSYS/MinGW/WindowsApps stub)
python -c "import sys; exit(0 if (3, 9) <= sys.version_info[:2] <= (3, 13) and 'msys' not in sys.executable.lower() and 'mingw' not in sys.executable.lower() and 'windowsapps' not in sys.executable.lower() else 1)" >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :init_venv
)

:: Strategy E: Check Conda installations
if exist "%USERPROFILE%\miniconda3\python.exe" (
    set "PY_CMD=%USERPROFILE%\miniconda3\python.exe"
    goto :init_venv
)
if exist "%USERPROFILE%\anaconda3\python.exe" (
    set "PY_CMD=%USERPROFILE%\anaconda3\python.exe"
    goto :init_venv
)

:: Strategy F: Fallback to any Python >= 3.8
py -3 -c "import sys; exit(0 if sys.version_info >= (3, 8) and 'msys' not in sys.executable.lower() else 1)" >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto :init_venv
)

python -c "import sys; exit(0 if sys.version_info >= (3, 8) and 'msys' not in sys.executable.lower() and 'windowsapps' not in sys.executable.lower() else 1)" >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :init_venv
)

:: No Python found on this machine
echo ================================================================
echo [ERROR] Python 3.9 ~ 3.13 was not found on this computer!
echo Windows Dynamic Island requires Python 3.9+ to run.
echo ================================================================
echo.

where winget >nul 2>nul
if not errorlevel 1 (
    echo Windows Package Manager (winget) detected.
    set /p "AUTO_IN=Install official Python 3.12 automatically? (Y/N, default: Y): "
    if /i "%AUTO_IN%"=="" set "AUTO_IN=Y"
    if /i "%AUTO_IN%"=="Y" (
        winget install -e --id Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements
        echo.
        echo [OK] Python installation finished! Please run run.bat again.
        pause
        exit /b 0
    )
)

echo Opening Python official download page in browser:
echo https://www.python.org/downloads/
echo.
echo NOTE: Make sure to check [Add python.exe to PATH] during installation!
echo.
start https://www.python.org/downloads/
pause
exit /b 1

:init_venv
%PY_CMD% "%~dp0bootstrap.py" --check-only
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment initialization failed.
    pause
    exit /b 1
)

:check_and_launch
:: 3. Check and install dependencies if missing
"%~dp0.venv\Scripts\python.exe" "%~dp0bootstrap.py" --check-only
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency preparation failed.
    pause
    exit /b 1
)

:: 4. Check for console / debug mode argument
if "%1"=="--debug" goto :run_debug
if "%1"=="--console" goto :run_debug

:: Normal launch: detached background execution using start
start "" "%~dp0.venv\Scripts\python.exe" "%~dp0main.py"

echo ================================================================
echo  Windows Dynamic Island has started in the background.
echo  Pill is floating at the top center of your primary screen.
echo ================================================================
echo This window will close in 2 seconds...
ping 127.0.0.1 -n 2 >nul 2>&1
exit /b 0

:run_debug
echo [DEBUG MODE] Dynamic Island running with console output...
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py" --debug
pause
exit /b 0
