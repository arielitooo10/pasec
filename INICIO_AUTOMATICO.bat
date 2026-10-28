@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "DESTINO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PASEC.bat"
echo @echo off> "%DESTINO%"
echo start "PASEC" /min "%~dp02_INICIAR.bat">> "%DESTINO%"
echo PASEC arrancara solo cada vez que se inicie sesion en esta computadora.
echo Para quitarlo, borra este archivo: %DESTINO%
echo.
pause
