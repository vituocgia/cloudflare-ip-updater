@echo off
REM Cloudflare IP Updater Build Script

REM Create virtual environment
python -m venv venv
call venv\Scripts\activate

REM Install requirements
pip install -r requirements.txt

REM Build executable
pyinstaller --onefile --windowed ^
    --add-data "icon.ico:." ^
    --icon=icon.ico ^
    src\main.py

REM Clean up
deactivate

echo Build completed. Check the 'dist' folder for the executable.
pause