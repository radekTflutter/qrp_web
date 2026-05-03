# Instalacja autostartu serwera Django QRP

## Metoda 1: Folder Autostart (Najprostsza)

1. Naciśnij `Win + R`
2. Wpisz: `shell:startup` i naciśnij Enter
3. Skopiuj plik `start_server.bat` lub `start_server_hidden.bat` do tego folderu
4. Zmień nazwę pliku na `QRP_Server.bat` (opcjonalnie)

## Metoda 2: Task Scheduler (Zalecana - uruchamia się nawet przed logowaniem)

1. Otwórz **Task Scheduler** (Zaplanowane zadania)
   - Naciśnij `Win + R`, wpisz `taskschd.msc` i naciśnij Enter

2. Kliknij **Create Basic Task** (Utwórz podstawowe zadanie)

3. Wprowadź:
   - **Name**: `QRP Django Server`
   - **Description**: `Uruchamia serwer Django QRP po restarcie systemu`

4. **Trigger** (Wyzwalacz):
   - Wybierz **When the computer starts** (Gdy komputer się uruchamia)

5. **Action** (Akcja):
   - Wybierz **Start a program** (Uruchom program)
   - **Program/script**: `C:\QRP\start_server.bat`
   - **Start in**: `C:\QRP`

6. **Conditions** (Warunki):
   - Odznacz **Start the task only if the computer is on AC power** (jeśli chcesz, aby działało również na baterii)

7. **Settings** (Ustawienia):
   - Zaznacz **Run task as soon as possible after a scheduled start is missed**
   - Zaznacz **If the task fails, restart every**: `1 minute` (opcjonalnie)

8. Kliknij **Finish**

## Metoda 3: Usługa Windows (Zaawansowana)

Aby uruchomić jako usługę Windows, użyj narzędzia `NSSM` (Non-Sucking Service Manager):

1. Pobierz NSSM z: https://nssm.cc/download
2. Rozpakuj do `C:\QRP\nssm\`
3. Uruchom jako Administrator:
   ```
   C:\QRP\nssm\nssm.exe install QRP_Django_Server
   ```
4. W oknie NSSM ustaw:
   - **Path**: `C:\Windows\System32\cmd.exe`
   - **Startup directory**: `C:\QRP`
   - **Arguments**: `/c C:\QRP\start_server.bat`
5. Kliknij **Install service**

## Uwagi

- **Port 8000**: Jeśli port 8000 jest zajęty, zmień w pliku `.bat` na inny port (np. `8001`)
- **Firewall**: Upewnij się, że Windows Firewall pozwala na połączenia na porcie 8000
- **Logi**: Aby zobaczyć logi serwera, użyj `start_server.bat` zamiast `start_server_hidden.bat`
- **Środowisko wirtualne**: Upewnij się, że ścieżka do `venv` jest poprawna (`C:\QRP\venv`)

## Testowanie

Aby przetestować, czy skrypt działa:
1. Uruchom `start_server.bat` ręcznie
2. Sprawdź, czy serwer działa na `http://localhost:8000`
3. Jeśli działa, możesz dodać do autostartu

## Wyłączenie autostartu

- **Metoda 1**: Usuń plik z folderu `shell:startup`
- **Metoda 2**: Usuń zadanie z Task Scheduler
- **Metoda 3**: Uruchom `nssm.exe remove QRP_Django_Server`
