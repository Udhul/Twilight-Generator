@echo off
setlocal

:: Check if virtual environment exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate
    echo Installing requirements...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
    pip install --quiet -r requirements.txt 2>nul
)

:: Launch the application
echo Launching Twilight Generator
python twilight_ui.py

deactivate
