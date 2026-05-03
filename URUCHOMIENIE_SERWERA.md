# Jak uruchomić serwer Django aby działał pod adresem DNS

## Problem

Aby aplikacja była dostępna pod adresem `http://qrp-l9.canpack.ad`, serwer Django musi:
1. Nasłuchiwać na wszystkich interfejsach sieciowych (0.0.0.0), nie tylko localhost
2. Akceptować żądania z domeny `.canpack.ad`

## Rozwiązanie

### Metoda 1: Uruchomienie ręczne (Development/Testowanie)

```bash
# W folderze projektu
python manage.py runserver 0.0.0.0:8000
```

Lub na Windows:
```cmd
cd C:\QRP_APP
venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
```

**Ważne**: `0.0.0.0:8000` oznacza, że serwer będzie nasłuchiwał na wszystkich interfejsach sieciowych na porcie 8000.

### Metoda 2: Użycie skryptu batch (Windows)

Użyj pliku `start_service.bat`:

```cmd
start_service.bat
```

Lub zmodyfikuj go aby nasłuchiwał na `0.0.0.0:8000` (już jest skonfigurowane).

### Metoda 3: Instalacja jako usługa Windows (Produkcja)

Najlepsza metoda dla środowiska produkcyjnego - użyj skryptu instalacyjnego:

```powershell
# Jako administrator
.\install_service.ps1
```

To automatycznie skonfiguruje usługę z `0.0.0.0:8000`.

## Weryfikacja

### 1. Sprawdź czy serwer działa

```bash
# Sprawdź czy port 8000 jest otwarty
netstat -an | findstr :8000
```

Powinieneś zobaczyć coś podobnego:
```
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING
```

### 2. Sprawdź DNS

```cmd
ping qrp-l9.canpack.ad
nslookup qrp-l9.canpack.ad
```

DNS powinien zwrócić IP serwera Django.

### 3. Sprawdź dostęp przez IP

Najpierw przetestuj czy aplikacja działa przez IP:
```
http://[IP_SERWERA]:8000
```

### 4. Sprawdź dostęp przez DNS

Jeśli działa przez IP, sprawdź DNS:
```
http://qrp-l9.canpack.ad
```

## Rozwiązywanie problemów

### Problem: Serwer nie startuje na 0.0.0.0:8000

**Rozwiązanie**:
1. Sprawdź czy port 8000 nie jest zajęty:
   ```cmd
   netstat -ano | findstr :8000
   ```
2. Jeśli port jest zajęty, zmień port:
   ```bash
   python manage.py runserver 0.0.0.0:8080
   ```
   I zaktualizuj DNS/konfigurację.

### Problem: "Bad Request (400)" przy próbie dostępu przez DNS

**Rozwiązanie**:
1. Sprawdź `ALLOWED_HOSTS` w `settings.py` - powinno zawierać `.canpack.ad`
2. Sprawdź logi Django - zobaczysz dokładny błąd
3. Upewnij się, że middleware `HostnameRoutingMiddleware` jest dodane

### Problem: DNS nie rozwiązuje adresu

**Rozwiązanie**:
1. Sprawdź konfigurację DNS w Active Directory
2. Wyczyść cache DNS:
   ```cmd
   ipconfig /flushdns
   ```
3. Sprawdź czy rekord DNS istnieje:
   ```cmd
   nslookup qrp-l9.canpack.ad
   ```

### Problem: Firewall blokuje połączenie

**Rozwiązanie**:
1. Otwórz port 8000 w Windows Firewall:
   ```powershell
   New-NetFirewallRule -DisplayName "QRP App Django" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
   ```
2. Lub przez GUI: Windows Defender Firewall → Advanced Settings → Inbound Rules → New Rule

### Problem: Aplikacja działa lokalnie, ale nie z innych komputerów

**Rozwiązanie**:
- Upewnij się, że używasz `0.0.0.0:8000` a nie `127.0.0.1:8000` lub `localhost:8000`
- `127.0.0.1` i `localhost` akceptują tylko lokalne połączenia
- `0.0.0.0` akceptuje połączenia ze wszystkich interfejsów

## Bezpieczeństwo

⚠️ **UWAGA**: W produkcji nie używaj wbudowanego serwera Django (`runserver`). 

Użyj:
- **Gunicorn** + **Nginx** (Linux)
- **Waitress** + **IIS** (Windows)
- **Uvicorn** + **Nginx** (ASGI)

Ale dla testów i developmentu `runserver 0.0.0.0:8000` jest wystarczające.

## Szybka komenda do uruchomienia (Windows)

Zapisz jako `start.bat` w folderze projektu:

```batch
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
echo Uruchamianie serwera Django na 0.0.0.0:8000...
python manage.py runserver 0.0.0.0:8000
pause
```

Uruchom przez podwójne kliknięcie.
