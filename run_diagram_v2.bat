@echo off
setlocal
title Kolos diagram v2
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" "%~dp0Diagram_new.py"
) else (
    py -3 "%~dp0Diagram_new.py"
)

if errorlevel 1 (
    echo.
    echo Diagram v2 failed. Check Python, Pillow, and Li_db_v1_4.db.
    pause
)

endlocal
