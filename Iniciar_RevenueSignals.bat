@echo off
title Revenue Signals Agent
cd /d "%~dp0"
REM Prioriza el codigo fuente (siempre la ultima version); el .exe solo si no hay Python
where python >nul 2>nul
if %errorlevel%==0 (
  python -m rsa app
  goto :fin
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -m rsa app
  goto :fin
)
if exist RevenueSignals.exe (
  RevenueSignals.exe app
) else (
  echo No se encontro Python. Instalalo desde python.org marcando "Add Python to PATH".
)
:fin
pause
