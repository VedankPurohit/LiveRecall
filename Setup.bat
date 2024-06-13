@echo off
setlocal

REM Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Downloading and installing Python...
    REM Replace the URL below with the URL of the Python installer you want to use
    set PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.10.6/python-3.10.6-amd64.exe
    set PYTHON_INSTALLER=python_installer.exe

    REM Download Python installer
    powershell -Command "Invoke-WebRequest -Uri %PYTHON_INSTALLER_URL% -OutFile %PYTHON_INSTALLER%"

    REM Install Python
    %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1

    REM Clean up installer
    del %PYTHON_INSTALLER%
)

REM Upgrade pip to the latest version
python -m pip install --upgrade pip

REM Install packages from requirements.txt
pip install -r requirements.txt

echo All done!
pause
