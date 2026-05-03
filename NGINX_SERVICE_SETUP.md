# Konfiguracja Nginx + Django jako usługi Windows

## Przegląd

Konfiguracja Nginx (reverse proxy) i Django jako dwóch osobnych usług Windows, które startują automatycznie przy uruchomieniu systemu.

## Krok 1: Zainstaluj Django jako usługę (port 8000)

Wykonaj instrukcje z `windows_service_setup.md` lub użyj skryptu:

```powershell
# Jako administrator
.\install_service.ps1
```

To utworzy usługę `QRPAppService` która uruchamia Django na `127.0.0.1:8000`.

## Krok 2: Zainstaluj Nginx jako usługę (port 80)

### Opcja A: NSSM (Zalecane)

```powershell
# Jako administrator
# Załóżmy że Nginx jest w C:\nginx

C:\nssm\win64\nssm.exe install NginxService "C:\nginx\nginx.exe"
C:\nssm\win64\nssm.exe set NginxService AppDirectory "C:\nginx"
C:\nssm\win64\nssm.exe set NginxService Description "Nginx Reverse Proxy for QRP App"
C:\nssm\win64\nssm.exe set NginxService Start SERVICE_AUTO_START

# Opcjonalnie: logi
New-Item -ItemType Directory -Path "C:\nginx\logs" -Force
C:\nssm\win64\nssm.exe set NginxService AppStdout "C:\nginx\logs\service_stdout.log"
C:\nssm\win64\nssm.exe set NginxService AppStderr "C:\nginx\logs\service_stderr.log"
```

### Opcja B: Skrypt instalacyjny

Zapisz jako `install_nginx_service.ps1`:

```powershell
# install_nginx_service.ps1
# Wymaga uruchomienia jako administrator

param(
    [string]$NginxPath = "C:\nginx",
    [string]$NSSMPath = "C:\nssm\win64\nssm.exe"
)

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "BŁĄD: Ten skrypt musi być uruchomiony jako administrator!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "$NginxPath\nginx.exe")) {
    Write-Host "BŁĄD: Nginx nie został znaleziony w: $NginxPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $NSSMPath)) {
    Write-Host "BŁĄD: NSSM nie został znaleziony w: $NSSMPath" -ForegroundColor Red
    Write-Host "Pobierz NSSM z: https://nssm.cc/download" -ForegroundColor Yellow
    exit 1
}

Write-Host "Instalowanie usługi Nginx..." -ForegroundColor Green

# Sprawdź czy usługa już istnieje
$Service = Get-Service -Name "NginxService" -ErrorAction SilentlyContinue
if ($Service) {
    Write-Host "Zatrzymywanie istniejącej usługi..." -ForegroundColor Yellow
    Stop-Service -Name "NginxService" -ErrorAction SilentlyContinue -Force
    Start-Sleep -Seconds 2
    & $NSSMPath remove NginxService confirm 2>&1 | Out-Null
    Start-Sleep -Seconds 2
}

# Zainstaluj usługę
& $NSSMPath install NginxService "$NginxPath\nginx.exe"

if ($LASTEXITCODE -ne 0) {
    Write-Host "BŁĄD: Nie udało się zainstalować usługi!" -ForegroundColor Red
    exit 1
}

# Skonfiguruj usługę
& $NSSMPath set NginxService AppDirectory $NginxPath | Out-Null
& $NSSMPath set NginxService Description "Nginx Reverse Proxy for QRP App" | Out-Null
& $NSSMPath set NginxService Start SERVICE_AUTO_START | Out-Null

# Utwórz folder na logi (jeśli nie istnieje)
$LogsPath = Join-Path $NginxPath "logs"
if (-not (Test-Path $LogsPath)) {
    New-Item -ItemType Directory -Path $LogsPath -Force | Out-Null
}

& $NSSMPath set NginxService AppStdout (Join-Path $LogsPath "service_stdout.log") | Out-Null
& $NSSMPath set NginxService AppStderr (Join-Path $LogsPath "service_stderr.log") | Out-Null

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Usługa Nginx zainstalowana pomyślnie!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Uruchom usługę:" -ForegroundColor Cyan
Write-Host "  net start NginxService" -ForegroundColor White
Write-Host "  lub: Start-Service NginxService" -ForegroundColor White
Write-Host ""

$startNow = Read-Host "Czy chcesz uruchomić usługę teraz? (T/N)"
if ($startNow -eq 'T' -or $startNow -eq 't') {
    Write-Host "Uruchamianie usługi..." -ForegroundColor Green
    Start-Service NginxService
    Start-Sleep -Seconds 2
    $status = Get-Service NginxService
    if ($status.Status -eq 'Running') {
        Write-Host "Usługa uruchomiona pomyślnie!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Aplikacja powinna być dostępna pod:" -ForegroundColor Cyan
        Write-Host "  http://qrp-l9.canpack.ad" -ForegroundColor White
    } else {
        Write-Host "BŁĄD: Nie udało się uruchomić usługi!" -ForegroundColor Red
        Write-Host "Sprawdź logi w: $LogsPath" -ForegroundColor Yellow
    }
}
```

Uruchom:
```powershell
.\install_nginx_service.ps1
```

## Krok 3: Skonfiguruj nginx.conf

Upewnij się, że `C:\nginx\conf\nginx.conf` ma konfigurację reverse proxy (zobacz `NGINX_CONFIG.md`).

## Krok 4: Weryfikacja konfiguracji

### Sprawdź obie usługi:

```powershell
# Status usług
Get-Service QRPAppService, NginxService

# Powinny być w statusie "Running"
```

### Sprawdź porty:

```cmd
netstat -an | findstr ":80 :8000"
```

Powinieneś zobaczyć:
```
TCP    0.0.0.0:80             0.0.0.0:0              LISTENING  (Nginx)
TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING  (Django)
```

### Sprawdź w przeglądarce:

1. `http://localhost:8000` - bezpośrednio Django (powinno działać)
2. `http://qrp-l9.canpack.ad` - przez Nginx (powinno działać bez portu)

## Zarządzanie usługami

```powershell
# Uruchom obie usługi
Start-Service QRPAppService
Start-Service NginxService

# Zatrzymaj obie usługi
Stop-Service QRPAppService
Stop-Service NginxService

# Restart obu usług
Restart-Service QRPAppService
Restart-Service NginxService

# Status
Get-Service QRPAppService, NginxService
```

## Kolejność startu

**WAŻNE**: Nginx może się uruchomić przed Django. To nie jest problem, ponieważ:
- Nginx będzie próbował połączyć się z Django przy pierwszym żądaniu
- Jeśli Django nie jest jeszcze uruchomione, dostaniesz 502 Bad Gateway
- Po uruchomieniu Django, kolejne żądania będą działać

Aby zagwarantować kolejność startu, możesz użyć zależności usług:

```powershell
# Ustaw zależność: Nginx startuje po Django
Set-Service -Name NginxService -DependentServices QRPAppService
```

Lub skonfiguruj opóźnienie startu Nginx w NSSM:
```powershell
C:\nssm\win64\nssm.exe set NginxService AppThrottle 1500
```

## Automatyczny start przy uruchomieniu systemu

Oba usługi są skonfigurowane jako `SERVICE_AUTO_START`, więc uruchomią się automatycznie przy starcie Windows.

## Logi

- **Django**: `C:\QRP_APP\logs\stdout.log` i `stderr.log`
- **Nginx**: `C:\nginx\logs\error.log` i `access.log`
- **Nginx Service**: `C:\nginx\logs\service_stdout.log` i `service_stderr.log`

## Rozwiązywanie problemów

### Problem: 502 Bad Gateway

**Rozwiązanie**:
1. Sprawdź czy Django działa:
   ```powershell
   Get-Service QRPAppService
   ```
2. Sprawdź czy Django nasłuchuje na porcie 8000:
   ```cmd
   netstat -an | findstr :8000
   ```
3. Sprawdź logi Django w `C:\QRP_APP\logs\`

### Problem: Nginx nie startuje

**Rozwiązanie**:
1. Sprawdź logi: `C:\nginx\logs\error.log`
2. Sprawdź konfigurację:
   ```cmd
   cd C:\nginx
   nginx.exe -t
   ```
3. Sprawdź czy port 80 nie jest zajęty:
   ```cmd
   netstat -ano | findstr :80
   ```

### Problem: Port 80 zajęty

**Rozwiązanie**:
1. Zatrzymaj IIS:
   ```powershell
   Stop-Service W3SVC
   Set-Service W3SVC -StartupType Disabled
   ```
2. Lub zmień port Nginx na inny (np. 8080) i zaktualizuj DNS

## Podsumowanie

Po skonfigurowaniu:
- ✅ Django działa jako usługa `QRPAppService` na porcie 8000
- ✅ Nginx działa jako usługa `NginxService` na porcie 80
- ✅ Obie usługi startują automatycznie przy uruchomieniu Windows
- ✅ Aplikacja dostępna pod `http://qrp-l9.canpack.ad` (bez portu)
