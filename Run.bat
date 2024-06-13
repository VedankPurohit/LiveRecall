@echo off
setlocal

REM Check if Streamlit is installed
streamlit --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Streamlit is not installed. Installing Streamlit...
    pip install streamlit
)

REM Run the Streamlit application
streamlit run app.py

endlocal
