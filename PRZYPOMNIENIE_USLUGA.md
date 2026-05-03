# Przypomnienie: Instalacja jako usługa Windows 11

## Szybki przewodnik

### Krok 1: Pobierz NSSM

1. Pobierz NSSM: https://nssm.cc/download
2. Rozpakuj np. do `C:\nssm`

### Krok 2: Uruchom skrypt instalacyjny (NAJPROSTSZE)

```powershell
# Otwórz PowerShell jako administrator
cd C:\QRP_APP
.\install_service.ps1
```

**To wszystko!** Skrypt automatycznie:
- Sprawdzi wszystkie wymagania
- Zainstaluje usługę `QRPAppService`
- Skonfiguruje autostart
- Utworzy logi

### Krok 3: Uruchom usługę

```powershell
net start QRPAppService
```

Lub po prostu zrestartuj komputer - usługa uruchomi się automatycznie!

---

## Alternatywa: Instalacja ręczna (jeśli skrypt nie działa)

### Krok 1: Zainstaluj usługę

```powershell
# Jako administrator
cd C:\QRP_APP

C:\nssm\win64\nssm.exe install QRPAppService "C:\QRP_APP\venv\Scripts\python.exe" "manage.py runserver 0.0.0.0:8000"
```

### Krok 2: Skonfiguruj parametry

```powershell
# Folder roboczy
C:\nssm\win64\nssm.exe set QRPAppService AppDirectory "C:\QRP_APP"

# Opis
C:\nssm\win64\nssm.exe set QRPAppService Description "QRP Control System - Django Application"

# Autostart
C:\nssm\win64\nssm.exe set QRPAppService Start SERVICE_AUTO_START

# Logi
New-Item -ItemType Directory -Path "C:\QRP_APP\logs" -Force
C:\nssm\win64\nssm.exe set QRPAppService AppStdout "C:\QRP_APP\logs\stdout.log"
C:\nssm\win64\nssm.exe set QRPAppService AppStderr "C:\QRP_APP\logs\stderr.log"
```

### Krok 3: Uruchom usługę

```powershell
net start QRPAppService
```

---

## Zarządzanie usługą

```powershell
# Status
Get-Service QRPAppService

# Uruchom
net start QRPAppService
# lub
Start-Service QRPAppService

# Zatrzymaj
net stop QRPAppService
# lub
Stop-Service QRPAppService

# Restart
Restart-Service QRPAppService

# Odinstaluj (jeśli potrzeba)
C:\nssm\win64\nssm.exe remove QRPAppService confirm
```

---

## Weryfikacja

Po instalacji sprawdź:

1. **Status usługi**:
   ```powershell
   Get-Service QRPAppService
   ```
   Powinno pokazać: `Running`

2. **Przeglądarka**:
   ```
   http://localhost:8000
   ```

3. **Logi** (jeśli problemy):
   ```
   C:\QRP_APP\logs\stdout.log
   C:\QRP_APP\logs\stderr.log
   ```

---

## Ważne informacje

- ✅ Usługa uruchamia się automatycznie przy starcie Windows
- ✅ Serwer działa na `0.0.0.0:8000` (dostępne z sieci)
- ✅ Jeśli chcesz bez portu (`http://qrp-l9.canpack.ad`), zobacz `NGINX_SERVICE_SETUP.md`
- ✅ Wszystkie ścieżki (`C:\QRP_APP`, `C:\nssm`) dostosuj do swojej instalacji

---

## Rozwiązywanie problemów

### Port 8000 zajęty

```powershell
# Sprawdź co używa portu
netstat -ano | findstr :8000

# Zatrzymaj proces lub zmień port w konfiguracji usługi
```

### Usługa nie startuje

1. Sprawdź logi w `C:\QRP_APP\logs\`
2. Sprawdź czy Python i venv są poprawnie skonfigurowane
3. Sprawdź czy ścieżki w NSSM są poprawne

### Zmiana portu

```powershell
# Zatrzymaj usługę
net stop QRPAppService

# Zmień parametr
C:\nssm\win64\nssm.exe set QRPAppService AppParameters "manage.py runserver 0.0.0.0:8080"

# Uruchom ponownie
net start QRPAppService
```

---

## Pełna dokumentacja

Zobacz: **`windows_service_setup.md`** - szczegółowe instrukcje wszystkich metod
