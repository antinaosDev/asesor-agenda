@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python register_events.py
pause
