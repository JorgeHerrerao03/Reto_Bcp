@echo off
title Revenue Signals Agent
cd /d "%~dp0"
REM Prioriza el codigo fuente (siempre la ultima version). Comprueba que el interprete REALMENTE ejecute
REM (el alias de WindowsApps existe pero puede fallar) y si no, prueba py y luego el .exe.
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if %errorlevel%==0 (
  python -m rsa app
  goto :fin
)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if %errorlevel%==0 (
  py -3 -m rsa app
  goto :fin
)
if exist RevenueSignals.exe (
  echo Python 3.9+ no disponible: usando RevenueSignals.exe ^(puede ser una version anterior del codigo^)
  RevenueSignals.exe app
) else (
  echo No se encontro Python 3.9+. Instalalo desde python.org marcando "Add Python to PATH".
)
:fin
pause
