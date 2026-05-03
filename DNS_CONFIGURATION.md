# Konfiguracja DNS dla QRP App

## Przegląd

Aplikacja QRP może być dostępna przez przyjazne adresy DNS zamiast IP:
- `http://qrp-l9.canpack.ad` - dla linii L9 (bez portu!)
- `http://qrp-l2.canpack.ad` - dla linii L2 (bez portu!)
- itd.

**WAŻNE**: Aby działało bez portu `:8000`, potrzebujesz **reverse proxy** (Nginx lub IIS), który nasłuchuje na porcie 80 i przekazuje żądania do Django na porcie 8000.

Zobacz:
- **NGINX_CONFIG.md** - konfiguracja Nginx (zalecane)
- **IIS_CONFIG.md** - konfiguracja IIS (Windows)

## Konfiguracja w Django

### 1. Ustaw identyfikator DNS w panelu admina

1. Przejdź do **Panelu Administracyjnego** → **Linie produkcyjne**
2. Wybierz linię (np. "Linia 9 - B4")
3. W polu **"Identyfikator DNS"** wprowadź identyfikator (np. `l9`)
4. Zapisz
5. Powtórz dla innych linii, które mają używać tego samego URL (np. "Linia 9 - B5" również z identyfikatorem `l9`)

**Ważne**: Wiele linii może mieć ten sam identyfikator DNS. Wszystkie linie z tym samym identyfikatorem będą dostępne pod tym samym URL (np. `qrp-l9.canpack.ad`), a użytkownik wybierze konkretną linię z listy.

### 2. Weryfikacja w Django

Middleware automatycznie rozpoznaje hostname i przypisuje aktywną linię do requestu.

Możesz sprawdzić w kodzie:
```python
if hasattr(request, 'active_line'):
    linia = request.active_line  # LiniaProdukcyjna dla tego hostname
    identifier = request.line_identifier  # np. "l9"
```

## Konfiguracja DNS w Active Directory (Windows Server)

### Metoda 1: DNS Manager (GUI)

1. Otwórz **DNS Manager** na serwerze DNS Active Directory
2. Rozwiń drzewo: **Forward Lookup Zones** → **canpack.ad**
3. Kliknij prawym przyciskiem na **canpack.ad** → **New Alias (CNAME)**
4. Wypełnij:
   - **Alias name**: `qrp-l9` (bez .canpack.ad)
   - **Fully qualified domain name (FQDN)**: `qrp-l9.canpack.ad`
   - **Target host**: `[IP_serwera_Django]` lub istniejący A record
   - Zaznacz **Update associated pointer (PTR) record**
5. Kliknij **OK**

**Uwaga**: Jeśli nie ma jeszcze A record dla serwera Django, najpierw utwórz A record:
- **Name**: `qrp-app` (lub podobne)
- **IP Address**: `[IP_serwera_Django]`

### Metoda 2: PowerShell (Dla masowej konfiguracji)

```powershell
# Importuj moduł DNS
Import-Module DnsServer

# IP serwera Django
$ServerIP = "10.11.1.100"  # ZASTĄP PRAWDZIWYM IP!

# Utwórz A record dla serwera (jeśli nie istnieje)
Add-DnsServerResourceRecordA -ZoneName "canpack.ad" -Name "qrp-app" -IPv4Address $ServerIP

# Utwórz CNAME dla linii L9
Add-DnsServerResourceRecordCName -ZoneName "canpack.ad" -Name "qrp-l9" -HostNameAlias "qrp-app.canpack.ad"

# Utwórz CNAME dla linii L2
Add-DnsServerResourceRecordCName -ZoneName "canpack.ad" -Name "qrp-l2" -HostNameAlias "qrp-app.canpack.ad"

# Sprawdź czy zostały utworzone
Get-DnsServerResourceRecord -ZoneName "canpack.ad" -Name "qrp-l9"
```

### Metoda 3: dnscmd (Command Line)

```cmd
# Utwórz A record (jeśli nie istnieje)
dnscmd [DNS_SERVER] /recordadd canpack.ad qrp-app A 10.11.1.100

# Utwórz CNAME dla linii L9
dnscmd [DNS_SERVER] /recordadd canpack.ad qrp-l9 CNAME qrp-app.canpack.ad

# Utwórz CNAME dla linii L2
dnscmd [DNS_SERVER] /recordadd canpack.ad qrp-l2 CNAME qrp-app.canpack.ad
```

Zastąp `[DNS_SERVER]` adresem IP lub nazwą serwera DNS.

## Konfiguracja serwera web (Opcjonalnie)

Jeśli używasz reverse proxy (nginx/Apache), możesz skonfigurować routing:

### Nginx przykład:

```nginx
server {
    listen 80;
    server_name qrp-l9.canpack.ad qrp-l2.canpack.ad *.canpack.ad;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Apache przykład:

```apache
<VirtualHost *:80>
    ServerName qrp-l9.canpack.ad
    ServerAlias qrp-*.canpack.ad
    
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    
    <Proxy *>
        Require all granted
    </Proxy>
</VirtualHost>
```

## Weryfikacja

Po konfiguracji DNS, sprawdź:

1. **Ping DNS**:
   ```cmd
   ping qrp-l9.canpack.ad
   ```
   Powinien zwrócić IP serwera Django.

2. **nslookup**:
   ```cmd
   nslookup qrp-l9.canpack.ad
   ```

3. **Przeglądarka**:
   Otwórz `http://qrp-l9.canpack.ad` w przeglądarce.

4. **Sprawdź w Django**:
   Middleware automatycznie wykryje hostname i przypisze odpowiednią linię do requestu.

## Troubleshooting

### Problem: DNS nie rozpoznaje nazwy

**Rozwiązanie**:
1. Sprawdź czy rekord DNS istnieje: `nslookup qrp-l9.canpack.ad`
2. Sprawdź czy serwer DNS jest dostępny
3. Wyczyść cache DNS: `ipconfig /flushdns` (Windows)

### Problem: Django zwraca 400 Bad Request

**Rozwiązanie**:
1. Sprawdź `ALLOWED_HOSTS` w `settings.py` - powinno zawierać `.canpack.ad`
2. Sprawdź logi Django
3. Upewnij się, że middleware `HostnameRoutingMiddleware` jest dodane do `MIDDLEWARE`

### Problem: Linia nie jest rozpoznawana

**Rozwiązanie**:
1. Sprawdź w panelu admina czy linia ma ustawiony `identyfikator_dns`
2. Sprawdź czy identyfikator w DNS zgadza się z identyfikatorem w Django (np. `l9` w obu miejscach)
3. Sprawdź czy linia jest aktywna (`aktywna=True`)

## Automatyczna konfiguracja DNS (Zaawansowane)

Możesz stworzyć skrypt PowerShell, który automatycznie utworzy rekordy DNS na podstawie linii w Django:

```powershell
# Przykład (wymaga dostępu do API Django lub bezpośredniego dostępu do bazy)
# To tylko przykład koncepcyjny

$Lines = Get-LinesFromDjango  # Pseudo-funkcja
foreach ($Line in $Lines) {
    $Identifier = $Line.identyfikator_dns
    if ($Identifier) {
        Add-DnsServerResourceRecordCName `
            -ZoneName "canpack.ad" `
            -Name "qrp-$Identifier" `
            -HostNameAlias "qrp-app.canpack.ad"
    }
}
```

## Bezpieczeństwo

1. **HTTPS**: W produkcji użyj HTTPS z certyfikatem SSL dla `*.canpack.ad`
2. **Firewall**: Upewnij się, że porty są odpowiednio skonfigurowane
3. **ALLOWED_HOSTS**: Nie używaj `['*']` w produkcji - ustaw konkretne hosty
