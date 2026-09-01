@echo off
title JARVIS AI - Permanent Bluetooth Self-Repair Engine
:: Self-elevate to Administrator
IF "%PROCESSOR_ARCHITECTURE%" EQU "amd64" (
>nul 2>&1 "%SYSTEMROOT%\SysWOW64\cacls.exe" "%SYSTEMROOT%\SysWOW64\config\system"
) ELSE (
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
)

if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params=%*
    echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)

pushd "%CD%"
CD /D "%~dp0"

cls
echo ========================================================
echo   JARVIS AI - PERMANENT BLUETOOTH SELF-REPAIR ENGINE
echo ========================================================
echo.
echo [1/4] Setting Bluetooth Services to AUTOMATIC in Windows Registry...
reg add "HKLM\SYSTEM\CurrentControlSet\Services\bthserv" /v Start /t REG_DWORD /d 2 /f >nul
reg add "HKLM\SYSTEM\CurrentControlSet\Services\BTAGService" /v Start /t REG_DWORD /d 2 /f >nul
sc config bthserv start= auto >nul
sc config BTAGService start= auto >nul

echo.
echo [2/4] Starting Bluetooth Support Services...
net start bthserv >nul 2>&1
net start BTAGService >nul 2>&1

echo.
echo [3/4] Rescanning PnP Hardware Devices and Refreshing USB Bus...
pnputil /scan-devices

echo.
echo [4/4] Re-enabling Bluetooth Device Adapters...
powershell -NoProfile -Command "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Enable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue"

echo.
echo ========================================================
echo   REPAIR COMPLETE! Opening Bluetooth Settings...
echo ========================================================
start ms-settings:bluetooth
echo.
echo Bluetooth service ab permanently AUTOMATIC par set ho chuki hai!
echo.
timeout /t 5
