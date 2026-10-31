@echo off
title Speechify Local - Neural Reader
cd /d "c:\Users\amr-a\.gemini\antigravity\playground\cryo-expanse"

:: Check if Speechify server on port 8000 is already running
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo    Speechify Local is already running in background!
    echo    Opening browser at http://localhost:8000 ...
    echo ============================================================
    echo.
    start "" http://localhost:8000
    ping 127.0.0.1 -n 2 >nul
    exit /b 0
)

:: Schedule browser to open after server boots
start "" /b cmd /c "ping 127.0.0.1 -n 3 >nul && start http://localhost:8000"

:: Launch Speechify server
"C:\Users\amr-a\AppData\Local\Programs\Python\Python311\python.exe" run_speechify.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server stopped with error.
    pause
)
