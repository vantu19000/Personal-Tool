@echo off
rem Double-click me to STOP the Personal-Tool server on port 8000.
setlocal enabledelayedexpansion
set "FOUND="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r "127\.0\.0\.1:8000.*LISTENING"') do (
    set "FOUND=1"
    taskkill /f /t /pid %%p >nul 2>&1
)
if defined FOUND (
    echo Da dung server (port 8000).
) else (
    echo Server khong dang chay (port 8000).
)
pause