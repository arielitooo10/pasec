@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Instalacion de PASEC
echo ==============================================
echo   PASEC - Instalacion (se hace una sola vez)
echo ==============================================
echo.

set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERROR] No se encontro Python en esta computadora.
    echo.
    echo Instalalo desde https://www.python.org/downloads/
    echo IMPORTANTE: en la primera pantalla del instalador marca la casilla
    echo "Add python.exe to PATH" y luego vuelve a abrir este archivo.
    echo.
    pause
    exit /b 1
)

echo [1/4] Creando el entorno de Python...
if not exist venv\Scripts\python.exe (
    %PY% -m venv venv
    if errorlevel 1 goto error
)

echo [2/4] Instalando los componentes (necesita internet, puede tardar)...
venv\Scripts\python.exe -m pip install --upgrade pip >nul
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error

echo [3/4] Creando la clave secreta de esta instalacion...
if not exist clave_secreta.txt (
    venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))" > clave_secreta.txt
)

echo [4/4] Preparando la base de datos...
venv\Scripts\python.exe init_db.py
if errorlevel 1 goto error

echo.
echo ==============================================
echo   Instalacion terminada.
echo   Siguiente paso: abre 2_INICIAR.bat
echo ==============================================
pause
exit /b 0

:error
echo.
echo [ERROR] Algo fallo. Toma una foto de esta pantalla y envia la.
pause
exit /b 1
