@echo off
setlocal
title Kolos graph viewer
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" "%~dp0graph_viewer.py"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 "%~dp0graph_viewer.py"
    ) else (
        python "%~dp0graph_viewer.py"
    )
)

if errorlevel 1 (
    echo.
    echo Graph viewer failed. Check Python, requirements, and db_v4.db.
    pause
)

endlocal
