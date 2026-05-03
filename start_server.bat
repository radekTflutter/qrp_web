@echo off
REM Skrypt do uruchamiania serwera Django QRP po restarcie komputera
REM Aplikacja znajduje się w C:\QRP

REM Przejdź do katalogu aplikacji
cd /d C:\QRP

REM Aktywuj środowisko wirtualne
call venv\Scripts\activate.bat

REM Uruchom serwer Django
REM Użyj 0.0.0.0:8000 aby serwer był dostępny z sieci
python manage.py runserver 0.0.0.0:8000

REM Jeśli serwer się zamknie, poczekaj 5 sekund i spróbuj ponownie
timeout /t 5 /nobreak
goto :eof
