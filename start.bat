@echo off
REM Szybkie uruchomienie serwera Django dla QRP App
REM Uruchamia serwer na 0.0.0.0:8000 aby działał pod adresem DNS

cd /d %~dp0

if not exist "venv\Scripts\activate.bat" (
    echo BLAD: Nie znaleziono wirtualnego srodowiska (venv)!
    echo Upewnij sie, ze jestes w folderze projektu.
    pause
    exit /b 1
)

echo ========================================
echo Uruchamianie serwera QRP App
echo ========================================
echo.

call venv\Scripts\activate.bat

echo Serwer uruchamiany na: 0.0.0.0:8000
echo Aplikacja bedzie dostepna pod:
echo   - http://localhost:8000
echo   - http://qrp-l9.canpack.ad (lub innym DNS skonfigurowanym)
echo.
echo Nacisnij Ctrl+C aby zatrzymac serwer
echo.

python manage.py runserver 0.0.0.0:8000

pause
