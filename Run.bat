@echo off
setlocal

REM Activate the Conda environment
conda activate AI

REM Check if Streamlit is installed
pip show streamlit >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Streamlit is not installed. Installing Streamlit...
    pip install streamlit
)

REM Run the Streamlit application
streamlit run app.py

endlocal
