@echo off
chcp 65001 >nul
cd /d "%~dp0"
venv\Scripts\python.exe respaldo.py
echo.
echo Copia la carpeta "respaldos" a una memoria USB o a la nube de la organización.
pause
