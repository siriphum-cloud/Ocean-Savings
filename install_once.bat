@echo off
cd /d "%~dp0"
echo Installing Streamlit (one time only)...
python -m pip install -r requirements.txt
echo.
echo Done! Now double-click run_app.bat
pause
