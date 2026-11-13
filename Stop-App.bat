@echo off
rem Double-click me to STOP the Personal-Tool server on port 9981.
setlocal enabledelayedexpansion
set "FOUND="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r "127\.0\.0\.1:9981.*LISTENING"') do (
    set "FOUND=1"
    taskkill /f /t /pid %%p >nul 2>&1
)
if defined FOUND (
    echo Da dung server (port 9981).
) else (
    echo Server khong dang chay (port 9981).
)
pause