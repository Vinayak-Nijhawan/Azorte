@echo off
cd /d "%~dp0"
echo Starting MOIL-GeoSync Streamlit application...
".\.venv\Scripts\streamlit.exe" run app.py
pause
