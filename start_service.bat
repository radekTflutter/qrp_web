@echo off
REM Skrypt startowy dla QRP App
REM Używany przez Task Scheduler lub do ręcznego uruchomienia
REM WAŻNE: Używa 0.0.0.0:8000 aby umożliwić dostęp przez DNS (qrp-l9.canpack.ad)

REM Zmień ścieżkę do folderu projektu
cd /d C:\QRP_APP

REM Aktywuj wirtualne środowisko
call venv\Scripts\activate.bat

REM Uruchom serwer Django na wszystkich interfejsach
REM 0.0.0.0:8000 jest wymagane aby aplikacja działała pod adresem DNS
REM Jeśli zmienisz na 127.0.0.1:8000 - aplikacja NIE BĘDZIE działać przez DNS!
echo Uruchamianie serwera Django na 0.0.0.0:8000...
echo Aplikacja bedzie dostepna pod: http://qrp-l9.canpack.ad (lub innym DNS)
echo Nacisnij Ctrl+C aby zatrzymac serwer
python manage.py runserver 0.0.0.0:8000
