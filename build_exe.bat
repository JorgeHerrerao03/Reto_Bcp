@echo off
REM Genera RevenueSignals.exe (Windows). Requiere Python 3.9+ e internet para instalar PyInstaller.
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller || goto :err
python -m PyInstaller --onefile --console --name RevenueSignals --distpath . --workpath build --specpath build --clean launcher.py || goto :err
echo.
echo Listo: RevenueSignals.exe
echo Debe quedar junto a las carpetas paquete\ y demo\ (o junto a ..\Revenue_Signals_Paquete_Candidatos_v3).
pause
exit /b 0
:err
echo Error al construir el ejecutable.
pause
exit /b 1
