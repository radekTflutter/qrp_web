# install_service.ps1
# Skrypt instalacji usługi Windows dla QRP App
# Wymaga uruchomienia jako administrator

param(
    [string]$ProjectPath = "C:\QRP_APP",
    [string]$NSSMPath = "C:\nssm\win64\nssm.exe"
)

# Sprawdź czy skrypt jest uruchomiony jako administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "BŁĄD: Ten skrypt musi być uruchomiony jako administrator!" -ForegroundColor Red
    Write-Host "Kliknij prawym przyciskiem na PowerShell i wybierz 'Run as administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Instalacja usługi QRP App" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Sprawdź czy NSSM istnieje
if (-not (Test-Path $NSSMPath)) {
    Write-Host "BŁĄD: NSSM nie został znaleziony w: $NSSMPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Pobierz NSSM z: https://nssm.cc/download" -ForegroundColor Yellow
    Write-Host "Lub zmień ścieżkę w parametrze -NSSMPath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Przykład:" -ForegroundColor Cyan
    Write-Host "  .\install_service.ps1 -NSSMPath 'D:\tools\nssm\win64\nssm.exe'" -ForegroundColor White
    exit 1
}

# Sprawdź czy projekt istnieje
if (-not (Test-Path $ProjectPath)) {
    Write-Host "BŁĄD: Projekt nie został znaleziony w: $ProjectPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Upewnij się, że ścieżka do projektu jest poprawna." -ForegroundColor Yellow
    Write-Host "Lub zmień ścieżkę w parametrze -ProjectPath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Przykład:" -ForegroundColor Cyan
    Write-Host "  .\install_service.ps1 -ProjectPath 'D:\Projects\QRP_APP'" -ForegroundColor White
    exit 1
}

# Utwórz folder na logi
$LogsPath = Join-Path $ProjectPath "logs"
if (-not (Test-Path $LogsPath)) {
    Write-Host "Tworzenie folderu na logi: $LogsPath" -ForegroundColor Green
    New-Item -ItemType Directory -Path $LogsPath -Force | Out-Null
}

# Python executable path
$PythonExe = Join-Path $ProjectPath "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "BŁĄD: Python nie został znaleziony w: $PythonExe" -ForegroundColor Red
    Write-Host ""
    Write-Host "Upewnij się, że:" -ForegroundColor Yellow
    Write-Host "  1. Wirtualne środowisko (venv) jest utworzone" -ForegroundColor Yellow
    Write-Host "  2. Wszystkie zależności są zainstalowane (pip install -r requirements.txt)" -ForegroundColor Yellow
    exit 1
}

# Sprawdź czy manage.py istnieje
$ManagePy = Join-Path $ProjectPath "manage.py"
if (-not (Test-Path $ManagePy)) {
    Write-Host "BŁĄD: manage.py nie został znaleziony w: $ManagePy" -ForegroundColor Red
    exit 1
}

Write-Host "Parametry instalacji:" -ForegroundColor Cyan
Write-Host "  Projekt: $ProjectPath" -ForegroundColor White
Write-Host "  Python: $PythonExe" -ForegroundColor White
Write-Host "  NSSM: $NSSMPath" -ForegroundColor White
Write-Host "  Logi: $LogsPath" -ForegroundColor White
Write-Host ""

# Usuń istniejącą usługę jeśli istnieje
$Service = Get-Service -Name "QRPAppService" -ErrorAction SilentlyContinue
if ($Service) {
    Write-Host "Znaleziono istniejącą usługę QRPAppService" -ForegroundColor Yellow
    $response = Read-Host "Czy chcesz ją usunąć i zainstalować ponownie? (T/N)"
    if ($response -eq 'T' -or $response -eq 't') {
        Write-Host "Zatrzymywanie usługi..." -ForegroundColor Yellow
        Stop-Service -Name "QRPAppService" -ErrorAction SilentlyContinue -Force
        Start-Sleep -Seconds 2
        Write-Host "Usuwanie usługi..." -ForegroundColor Yellow
        & $NSSMPath remove QRPAppService confirm 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    } else {
        Write-Host "Instalacja anulowana." -ForegroundColor Yellow
        exit 0
    }
}

# Zainstaluj usługę
Write-Host ""
Write-Host "Instalowanie usługi QRPAppService..." -ForegroundColor Green
& $NSSMPath install QRPAppService $PythonExe "manage.py runserver 0.0.0.0:8000"

if ($LASTEXITCODE -ne 0) {
    Write-Host "BŁĄD: Nie udało się zainstalować usługi!" -ForegroundColor Red
    exit 1
}

# Ustaw parametry
Write-Host "Konfigurowanie parametrów usługi..." -ForegroundColor Green

& $NSSMPath set QRPAppService AppDirectory $ProjectPath | Out-Null
& $NSSMPath set QRPAppService Description "QRP Control System - Django Application" | Out-Null
& $NSSMPath set QRPAppService Start SERVICE_AUTO_START | Out-Null
& $NSSMPath set QRPAppService AppStdout (Join-Path $LogsPath "stdout.log") | Out-Null
& $NSSMPath set QRPAppService AppStderr (Join-Path $LogsPath "stderr.log") | Out-Null
& $NSSMPath set QRPAppService AppRotateFiles 1 | Out-Null
& $NSSMPath set QRPAppService AppRotateOnline 1 | Out-Null
& $NSSMPath set QRPAppService AppRotateSeconds 86400 | Out-Null
& $NSSMPath set QRPAppService AppRotateBytes 10485760 | Out-Null

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Usługa zainstalowana pomyślnie!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Dostępne komendy:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Uruchom usługę:" -ForegroundColor Yellow
Write-Host "    net start QRPAppService" -ForegroundColor White
Write-Host "    lub: Start-Service QRPAppService" -ForegroundColor White
Write-Host ""
Write-Host "  Zatrzymaj usługę:" -ForegroundColor Yellow
Write-Host "    net stop QRPAppService" -ForegroundColor White
Write-Host "    lub: Stop-Service QRPAppService" -ForegroundColor White
Write-Host ""
Write-Host "  Restart usługi:" -ForegroundColor Yellow
Write-Host "    Restart-Service QRPAppService" -ForegroundColor White
Write-Host ""
Write-Host "  Status usługi:" -ForegroundColor Yellow
Write-Host "    Get-Service QRPAppService" -ForegroundColor White
Write-Host ""
Write-Host "  Odinstaluj usługę:" -ForegroundColor Yellow
Write-Host "    & '$NSSMPath' remove QRPAppService confirm" -ForegroundColor White
Write-Host ""
Write-Host "Logi:" -ForegroundColor Yellow
Write-Host "  $LogsPath\stdout.log" -ForegroundColor White
Write-Host "  $LogsPath\stderr.log" -ForegroundColor White
Write-Host ""

$startNow = Read-Host "Czy chcesz uruchomić usługę teraz? (T/N)"
if ($startNow -eq 'T' -or $startNow -eq 't') {
    Write-Host "Uruchamianie usługi..." -ForegroundColor Green
    Start-Service QRPAppService
    Start-Sleep -Seconds 2
    $status = Get-Service QRPAppService
    if ($status.Status -eq 'Running') {
        Write-Host "Usługa uruchomiona pomyślnie!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Aplikacja powinna być dostępna pod:" -ForegroundColor Cyan
        Write-Host "  http://localhost:8000" -ForegroundColor White
    } else {
        Write-Host "BŁĄD: Nie udało się uruchomić usługi!" -ForegroundColor Red
        Write-Host "Sprawdź logi w: $LogsPath" -ForegroundColor Yellow
    }
}
