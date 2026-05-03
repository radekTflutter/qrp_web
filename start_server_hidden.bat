@echo off
REM Skrypt do uruchamiania serwera Django QRP w tle (bez okna konsoli)
REM Aplikacja znajduje się w C:\QRP

REM Przejdź do katalogu aplikacji
cd /d C:\QRP

REM Aktywuj środowisko wirtualne
call venv\Scripts\activate.bat

REM Uruchom serwer Django w tle (używa VBScript do ukrycia okna)
set VBScript=%temp%\start_server_hidden.vbs
echo Set WshShell = CreateObject("WScript.Shell") > %VBScript%
echo WshShell.Run "cmd /c python manage.py runserver 0.0.0.0:8000", 0, False >> %VBScript%
cscript //nologo %VBScript%
del %VBScript%
