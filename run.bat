@echo off
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
    python main.py
) else (
    py main.py
)
if errorlevel 1 pause
