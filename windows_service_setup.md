# Instalacja usługi Windows dla QRP App

## Metoda 1: Użycie NSSM (Zalecana)

NSSM (Non-Sucking Service Manager) to najprostszy sposób na utworzenie usługi Windows dla aplikacji Django.

### Krok 1: Pobierz NSSM

1. Pobierz NSSM z: https://nssm.cc/download
2. Rozpakuj archiwum (np. do `C:\nssm`)
3. Skopiuj odpowiednią wersję (64-bit lub 32-bit) do folderu projektu lub dodaj do PATH

### Krok 2: Uruchom instalację usługi

Otwórz **PowerShell jako administrator** i wykonaj:

```powershell
# Przejdź do folderu projektu (dostosuj ścieżkę)
cd C:\QRP_APP

# Zainstaluj usługę (dostosuj ścieżki do swojego środowiska)
C:\nssm\win64\nssm.exe install QRPAppService `
    "C:\QRP_APP\venv\Scripts\python.exe" `
    "C:\QRP_APP\manage.py runserver 0.0.0.0:8000"
```

### Krok 3: Skonfiguruj parametry usługi

```powershell
# Ustaw folder roboczy
C:\nssm\win64\nssm.exe set QRPAppService AppDirectory "C:\QRP_APP"

# Ustaw opis usługi
C:\nssm\win64\nssm.exe set QRPAppService Description "QRP Control System - Django Application"

# Ustaw typ startu (Automatyczny)
C:\nssm\win64\nssm.exe set QRPAppService Start SERVICE_AUTO_START

# Opcjonalnie: ustaw logowanie błędów
C:\nssm\win64\nssm.exe set QRPAppService AppStdout "C:\QRP_APP\logs\stdout.log"
C:\nssm\win64\nssm.exe set QRPAppService AppStderr "C:\QRP_APP\logs\stderr.log"
```

### Krok 4: Utwórz folder na logi (opcjonalnie)

```powershell
New-Item -ItemType Directory -Path "C:\QRP_APP\logs" -Force
```

### Krok 5: Uruchom usługę

```powershell
# Uruchom usługę
net start QRPAppService

# Lub przez NSSM
C:\nssm\win64\nssm.exe start QRPAppService
```

### Zarządzanie usługą

```powershell
# Uruchom
net start QRPAppService

# Zatrzymaj
net stop QRPAppService

# Restart
Restart-Service QRPAppService

# Odinstaluj (jeśli potrzeba)
C:\nssm\win64\nssm.exe remove QRPAppService confirm
```

---

## Metoda 2: Task Scheduler (Alternatywna)

Jeśli nie chcesz używać NSSM, możesz użyć Windows Task Scheduler.

### Krok 1: Utwórz skrypt startowy

Zapisz jako `start_service.bat` w folderze projektu:

```batch
@echo off
cd /d C:\QRP_APP
call venv\Scripts\activate.bat
python manage.py runserver 0.0.0.0:8000
```

### Krok 2: Utwórz zadanie w Task Scheduler

1. Otwórz **Task Scheduler** (Harmonogram zadań)
2. Kliknij **Create Task** (Utwórz zadanie)
3. Na karcie **General**:
   - **Name**: QRP App Service
   - **Description**: QRP Control System Django Application
   - Zaznacz **Run whether user is logged on or not**
   - Zaznacz **Run with highest privileges**
   - **Configure for**: Windows 11

4. Na karcie **Triggers**:
   - Kliknij **New**
   - **Begin the task**: At startup
   - Zaznacz **Enabled**

5. Na karcie **Actions**:
   - Kliknij **New**
   - **Action**: Start a program
   - **Program/script**: `C:\QRP_APP\start_service.bat`
   - **Start in**: `C:\QRP_APP`

6. Na karcie **Conditions**:
   - Odznacz **Start the task only if the computer is on AC power**

7. Na karcie **Settings**:
   - Zaznacz **Allow task to be run on demand**
   - Zaznacz **Run task as soon as possible after a scheduled start is missed**
   - **If the task fails, restart every**: 1 minute
   - **Attempt to restart up to**: 3 times

8. Kliknij **OK** i wprowadź hasło użytkownika

---

## Metoda 3: Skrypt instalacyjny (Automatyczny)

Zapisz jako `install_service.ps1` i uruchom jako administrator:

```powershell
# install_service.ps1
# Wymaga uruchomienia jako administrator

$ProjectPath = "C:\QRP_APP"  # DOSTOSUJ ŚCIEŻKĘ!
$NSSMPath = "C:\nssm\win64\nssm.exe"  # DOSTOSUJ ŚCIEŻKĘ DO NSSM!

Write-Host "Instalacja usługi QRP App..." -ForegroundColor Green

# Sprawdź czy NSSM istnieje
if (-not (Test-Path $NSSMPath)) {
    Write-Host "BŁĄD: NSSM nie został znaleziony w: $NSSMPath" -ForegroundColor Red
    Write-Host "Pobierz NSSM z: https://nssm.cc/download" -ForegroundColor Yellow
    exit 1
}

# Sprawdź czy projekt istnieje
if (-not (Test-Path $ProjectPath)) {
    Write-Host "BŁĄD: Projekt nie został znaleziony w: $ProjectPath" -ForegroundColor Red
    exit 1
}

# Utwórz folder na logi
$LogsPath = Join-Path $ProjectPath "logs"
if (-not (Test-Path $LogsPath)) {
    New-Item -ItemType Directory -Path $LogsPath -Force | Out-Null
}

# Python executable path
$PythonExe = Join-Path $ProjectPath "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "BŁĄD: Python nie został znaleziony w: $PythonExe" -ForegroundColor Red
    Write-Host "Upewnij się, że venv jest utworzony i aktywowany." -ForegroundColor Yellow
    exit 1
}

# Usuń istniejącą usługę jeśli istnieje
$Service = Get-Service -Name "QRPAppService" -ErrorAction SilentlyContinue
if ($Service) {
    Write-Host "Usuwanie istniejącej usługi..." -ForegroundColor Yellow
    Stop-Service -Name "QRPAppService" -ErrorAction SilentlyContinue
    & $NSSMPath remove QRPAppService confirm
    Start-Sleep -Seconds 2
}

# Zainstaluj usługę
Write-Host "Instalowanie usługi..." -ForegroundColor Green
& $NSSMPath install QRPAppService $PythonExe "manage.py runserver 0.0.0.0:8000"

# Ustaw parametry
Write-Host "Konfigurowanie parametrów usługi..." -ForegroundColor Green
& $NSSMPath set QRPAppService AppDirectory $ProjectPath
& $NSSMPath set QRPAppService Description "QRP Control System - Django Application"
& $NSSMPath set QRPAppService Start SERVICE_AUTO_START
& $NSSMPath set QRPAppService AppStdout (Join-Path $LogsPath "stdout.log")
& $NSSMPath set QRPAppService AppStderr (Join-Path $LogsPath "stderr.log")
& $NSSMPath set QRPAppService AppRotateFiles 1
& $NSSMPath set QRPAppService AppRotateOnline 1
& $NSSMPath set QRPAppService AppRotateSeconds 86400
& $NSSMPath set QRPAppService AppRotateBytes 10485760

Write-Host "Usługa zainstalowana pomyślnie!" -ForegroundColor Green
Write-Host ""
Write-Host "Aby uruchomić usługę, wykonaj:" -ForegroundColor Cyan
Write-Host "  net start QRPAppService" -ForegroundColor White
Write-Host ""
Write-Host "Aby zatrzymać usługę:" -ForegroundColor Cyan
Write-Host "  net stop QRPAppService" -ForegroundColor White
```

Uruchom:
```powershell
# Uruchom PowerShell jako administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install_service.ps1
```

---

## Weryfikacja działania

Po instalacji sprawdź czy usługa działa:

1. **Services (services.msc)** - znajdź "QRPAppService"
2. **PowerShell**: `Get-Service QRPAppService`
3. **Przeglądarka**: Otwórz http://localhost:8000

---

## Uwagi

- **Port 8000**: Upewnij się, że port 8000 nie jest zajęty przez inną aplikację
- **Firewall**: Może być wymagane dodanie wyjątku w zaporze Windows dla portu 8000
- **Logi**: Sprawdzaj logi w `C:\QRP_APP\logs\` w razie problemów
- **Ścieżki**: Wszystkie ścieżki w przykładach należy dostosować do swojej instalacji

---

## Konfiguracja z Nginx (bez portu w URL)

Jeśli chcesz, aby aplikacja działała pod `http://qrp-l9.canpack.ad` (bez `:8000`), skonfiguruj również Nginx jako usługę Windows.

Zobacz: **`NGINX_SERVICE_SETUP.md`** - instrukcje instalacji Nginx jako usługi oraz współpracy z Django.
