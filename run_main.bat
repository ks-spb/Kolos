@echo off
cd /d "%~dp0"
REM Kolos встроен в окно Glaz; запускается только Glaz.
py -3 "%~dp0Glaz\main.py"
if errorlevel 1 pause
