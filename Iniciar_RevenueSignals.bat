@echo off
title Revenue Signals Agent
cd /d "%~dp0"
if exist RevenueSignals.exe (
  RevenueSignals.exe app
  goto :fin
)
where python >nul 2>nul
if %errorlevel%==0 (python -m rsa app) else (py -m rsa app)
:fin
pause
