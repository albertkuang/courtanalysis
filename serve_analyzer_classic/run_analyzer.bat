@echo off
echo Starting AI Serve Analyzer local server...
echo.
echo Please leave this window open. The analyzer will open in your default browser.
echo Press Ctrl+C to stop the server when you are done.
echo.

cd /d "%~dp0"
start http://localhost:8001
python -m http.server 8001
