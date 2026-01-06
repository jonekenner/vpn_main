@echo off
echo Starting VPN Service...
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Starting Flask application...
python app.py
pause

