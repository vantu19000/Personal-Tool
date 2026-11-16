@echo off
chcp 65001 >nul
title Personal Tool - TEST Environment (Port 9982)

echo ===================================================
echo   KHỞI ĐỘNG PERSONAL TOOL - MÔI TRƯỜNG TEST
echo   Cổng: http://localhost:9982
echo   Database: personal_tool_test_db
echo ===================================================

set ENV_FILE=.env.test
set APP_ENV=testing

if exist .venv\Scripts\python.exe (
    set PYTHON_EXE=.venv\Scripts\python.exe
) else (
    set PYTHON_EXE=python
)

"%PYTHON_EXE%" main.py
pause
