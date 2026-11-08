@echo off
cd /d "%~dp0"
echo Starting Deep Ocean Savings... (close this window to stop)
python -m streamlit run app.py
pause
