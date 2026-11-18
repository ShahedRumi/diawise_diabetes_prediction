@echo off
setlocal
cd /d "%~dp0"
title DiaWise - Local Research Web Application
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_windows.ps1" %*
exit /b %errorlevel%
