@echo off
title Speechify Cloud + GPU Worker
cd /d "c:\Users\amr-a\.gemini\antigravity\playground\cryo-expanse"

echo.
echo ============================================================
echo       SPEECHIFY HYBRID - CLOUD + LOCAL GPU WORKER
echo ============================================================
echo.

:: 1. Launch local Python engine on port 8000 if not already running
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [1/3] Starting Local CUDA GPU Engine on port 8000...
    start "Speechify Engine" /min "C:\Users\amr-a\AppData\Local\Programs\Python\Python311\python.exe" run_speechify.py
    timeout /t 3 /nobreak >nul
) else (
    echo [1/3] Local CUDA GPU Engine is already running on port 8000.
)

:: 2. Launch Cloudflare Tunnel if not already running
tasklist /fi "imagename eq cloudflared.exe" 2>nul | findstr /i /c:"cloudflared.exe" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [2/3] Starting Cloudflare Tunnel to Render...
    start "Speechify Tunnel" /min "C:\Users\amr-a\AppData\Local\Programs\Python\Python311\python.exe" run_tunnel.py
    timeout /t 3 /nobreak >nul
) else (
    echo [2/3] Cloudflare Tunnel is already active.
)

:: 3. Open the live Render web app in default browser
echo [3/3] Opening Speechify Cloud Web App...
start "" "https://speechify-web.onrender.com"

echo.
echo ============================================================
echo   ALL SYSTEMS ONLINE AND READY!
echo ============================================================
echo   [Web Interface]  https://speechify-web.onrender.com
echo   [Local Engine]   http://localhost:8000 (NVIDIA CUDA)
echo   [Tunnel]         Cloudflare Secure Tunnel Active
echo ============================================================
echo.
echo You can minimize this window. Press any key to exit this launcher.
pause >nul
