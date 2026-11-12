@echo off
rem Ensure UTF-8 code page for proper Unicode characters
chcp 65001 >nul
title Windows Junk Cleaner

rem Comfortable window size (the script centres its layout to whatever width it gets)
mode con: cols=100 lines=48

rem Set Python I/O encoding to UTF-8
set PYTHONIOENCODING=utf-8

rem Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process py -ArgumentList '-Xutf8 \"%~dp0cleaner.py\" %*' -Verb runAs"
    timeout /t 2 >nul
    exit /b
)

rem Run the cleaner script (pass any arguments)
py -Xutf8 "%~dp0cleaner.py" %*
if errorlevel 1 (
    echo Script exited with error %errorlevel%
)
pause
