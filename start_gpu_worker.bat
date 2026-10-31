@echo off
title Speechify - Local GPU Worker Node
cd /d "%~dp0"

echo ============================================================
echo   Speechify GPU Worker Node (Kokoro + RVC v2)
echo ============================================================

:: Ensure local Speechify server is running on port 8000
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Starting local engine on port 8000...
    start "Speechify Engine" cmd /c "python run_speechify.py"
    ping 127.0.0.1 -n 3 >nul
) else (
    echo Local engine is already active on port 8000.
)

:: Check for FRP Client
if exist "oci_relay\frpc.exe" (
    echo Connecting to Oracle Cloud tunnel relay...
    oci_relay\frpc.exe -c oci_relay\frpc.toml
) else (
    echo.
    echo Notice: frpc.exe not found in oci_relay folder.
    echo Option A: Download frpc.exe from https://github.com/fatedier/frp/releases
    echo Option B: Or run Reverse SSH to Oracle Cloud:
    echo           ssh -R 8080:localhost:8000 ubuntu@YOUR_OCI_IP -N
    echo.
    pause
)
