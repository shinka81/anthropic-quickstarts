@echo off

REM Check Python version
python --version > temp.txt
for /f "tokens=2 delims=." %%i in (temp.txt) do set PYTHON_MINOR_VERSION=%%i
del temp.txt

if %PYTHON_MINOR_VERSION% gtr 12 (
    echo Python version 3.%PYTHON_MINOR_VERSION% detected. Python 3.12 or lower is required for setup to complete.
    echo If you have multiple versions of Python installed, you can set the correct one by adjusting setup.bat to use a specific version.
    exit /b 1
)

REM Check if cargo is installed
where cargo >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Cargo (the package manager for Rust^) is not present. This is required for one of this module's dependencies.
    echo See https://www.rust-lang.org/tools/install for installation instructions.
    exit /b 1
)

REM Create and activate virtual environment
python -m venv .venv
call .venv\Scripts\activate.bat

REM Install dependencies
python -m pip install --upgrade pip
pip install -r dev-requirements.txt
pre-commit install
