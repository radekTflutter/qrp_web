# Konfiguracja IIS jako Reverse Proxy dla QRP App (Windows)

## Przegląd

Konfiguracja IIS z Application Request Routing (ARR) do obsługi `http://qrp-l9.canpack.ad` bez portu.

## Wymagania

- Windows Server lub Windows 10/11 Pro z włączonym IIS
- Application Request Routing (ARR) module dla IIS
- URL Rewrite module dla IIS

## Instalacja

### Krok 1: Zainstaluj IIS

1. Otwórz **Turn Windows features on or off**
2. Zaznacz:
   - Internet Information Services
   - World Wide Web Services
   - Application Development Features → ASP.NET
3. Zainstaluj

### Krok 2: Zainstaluj ARR i URL Rewrite

1. Pobierz i zainstaluj **Application Request Routing**:
   https://www.iis.net/downloads/microsoft/application-request-routing
   
2. Pobierz i zainstaluj **URL Rewrite**:
   https://www.iis.net/downloads/microsoft/url-rewrite

### Krok 3: Skonfiguruj IIS

1. Otwórz **IIS Manager**

2. Kliknij prawym przyciskiem na **Sites** → **Add Website**

3. Wypełnij:
   - **Site name**: `QRP-App`
   - **Application pool**: Utwórz nowy (np. `QRPAppPool`)
   - **Physical path**: `C:\QRP_APP\static` (lub inna dowolna ścieżka)
   - **Binding**:
     - **Type**: `http`
     - **IP address**: `All Unassigned` lub konkretne IP
     - **Port**: `80`
     - **Host name**: `qrp-*.canpack.ad` (lub pozostaw puste dla wszystkich)

4. Kliknij **OK**

### Krok 4: Skonfiguruj Reverse Proxy

1. W **IIS Manager**, wybierz utworzony site (`QRP-App`)

2. Otwórz **URL Rewrite** (double-click)

3. Kliknij **Add Rule(s)...** → **Reverse Proxy**

4. Wypełnij:
   - **Inbound rules**: Pozostaw domyślne
   - **Rewrite rules**: `http://127.0.0.1:8000{R:0}`
   - Zaznacz **Enable reverse proxy**

5. Kliknij **OK**

### Krok 5: Edytuj web.config

Otwórz plik `web.config` w folderze site (lub utwórz go w `C:\QRP_APP\`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="ReverseProxyInboundRule1" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:8000/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_HOST" value="{HTTP_HOST}" />
                        <set name="HTTP_X_FORWARDED_PROTO" value="http" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        <httpProtocol>
            <customHeaders>
                <remove name="X-Powered-By" />
            </customHeaders>
        </httpProtocol>
    </system.webServer>
</configuration>
```

### Krok 6: Skonfiguruj Application Pool

1. Wybierz Application Pool (`QRPAppPool`)
2. Ustaw:
   - **.NET CLR Version**: `No Managed Code` (Django to Python, nie .NET)
   - **Managed Pipeline Mode**: `Integrated`

### Krok 7: Uruchom Django

```cmd
cd C:\QRP_APP
venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
```

### Krok 8: Sprawdź

Otwórz w przeglądarce: `http://qrp-l9.canpack.ad` (bez portu!)

## Alternatywna konfiguracja (Prostsza - przez PowerShell)

Utwórz `setup_iis.ps1`:

```powershell
# Uruchom jako administrator
Import-Module WebAdministration

# Utwórz Application Pool
New-WebAppPool -Name "QRPAppPool"
Set-ItemProperty IIS:\AppPools\QRPAppPool -Name managedRuntimeVersion -Value ""

# Utwórz Site
New-Website -Name "QRP-App" `
            -Port 80 `
            -HostHeader "qrp-*.canpack.ad" `
            -PhysicalPath "C:\QRP_APP" `
            -ApplicationPool "QRPAppPool"

# Włącz ARR
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "enabled" -value "True"

Write-Host "IIS skonfigurowany! Dodaj web.config z reverse proxy rules."
```

## Rozwiązywanie problemów

### Problem: 502.3 Bad Gateway

**Rozwiązanie**:
1. Sprawdź czy Django działa na porcie 8000
2. Sprawdź logi IIS: `C:\inetpub\logs\LogFiles`
3. Upewnij się, że ARR jest zainstalowany i włączony

### Problem: Port 80 zajęty przez inną aplikację

**Rozwiązanie**:
1. Zatrzymaj domyślny site IIS:
   ```powershell
   Stop-Website -Name "Default Web Site"
   ```
2. Lub zmień binding na inny port (np. 8080)

### Problem: Statyczne pliki nie ładują się

**Rozwiązanie**:
1. Dodaj handler dla statycznych plików w `web.config`
2. Lub przekieruj statyczne przez Django (zalecane dla developmentu)

## Uwagi

- W produkcji rozważ użycie HTTPS (port 443)
- IIS może być bardziej skomplikowany niż Nginx dla prostych przypadków
- Nginx jest lżejszy i łatwiejszy w konfiguracji dla reverse proxy
