@echo off
REM Cloudflare IP Updater Build Script

REM Create virtual environment if it doesn't exist
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Use existing version_info.txt file
echo Using existing version_info.txt file...

REM Build executable
echo Building executable...
pyinstaller --onefile --windowed ^
    --add-data "icon.ico;." ^
    --icon=icon.ico ^
    --version-file=version_info.txt ^
    --name=CloudflareIPUpdater ^
    src\main.py

REM Copy empty config file to dist folder
echo Creating empty config file in dist folder...
if not exist dist\updater_config.json (
  echo [] > dist\updater_config.json
)

REM Clean up
deactivate

echo Build completed. Check the 'dist' folder for the executable.
pause