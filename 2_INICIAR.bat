@echo off
chcp 65001 >nul
cd /d "%~dp0"
title PASEC - Sistema en marcha (no cerrar esta ventana)

if not exist venv\Scripts\python.exe (
    echo Primero ejecuta 1_INSTALAR.bat
    pause
    exit /b 1
)
if not exist clave_secreta.txt (
    echo Falta clave_secreta.txt. Ejecuta 1_INSTALAR.bat
    pause
    exit /b 1
)

set /p SECRET_KEY=<clave_secreta.txt
set PASEC_HTTPS=1
set PASEC_PROXY=1

echo Haciendo copia de seguridad...
venv\Scripts\python.exe respaldo.py

echo.
echo Iniciando PASEC...
venv\Scripts\python.exe servidor.py
echo.
echo El sistema se detuvo. Si no lo cerraste tu, toma una foto de esta pantalla.
pause
