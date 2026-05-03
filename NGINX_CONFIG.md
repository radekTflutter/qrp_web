# Konfiguracja Nginx jako Reverse Proxy dla QRP App

## Przegląd

Aby aplikacja działała pod `http://qrp-l9.canpack.ad` (bez portu `:8000`), potrzebujesz reverse proxy, który:
- Nasłuchuje na porcie 80 (domyślny HTTP)
- Przekazuje żądania do Django na porcie 8000
- Obsługuje wszystkie subdomeny `qrp-*.canpack.ad`

## Instalacja Nginx na Windows

### Krok 1: Pobierz Nginx

1. Pobierz Nginx dla Windows: http://nginx.org/en/download.html
2. Rozpakuj do np. `C:\nginx`

### Krok 2: Skonfiguruj Nginx

Edytuj plik `C:\nginx\conf\nginx.conf`:

```nginx
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    
    sendfile        on;
    keepalive_timeout  65;

    # Upstream dla Django (port 8000)
    upstream django {
        server 127.0.0.1:8000;
    }

    # Serwer dla wszystkich qrp-*.canpack.ad
    server {
        listen 80;
        server_name qrp-*.canpack.ad *.canpack.ad;

        client_max_body_size 50M;

        # Przekaż wszystkie żądania do Django
        location / {
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;
            
            # WebSocket support (jeśli potrzebne)
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Statyczne pliki (opcjonalnie, lepiej przez Django w development)
        location /static/ {
            alias C:/QRP_APP/staticfiles/;
        }

        location /media/ {
            alias C:/QRP_APP/media/;
        }
    }
}
```

**WAŻNE**: Zastąp `C:/QRP_APP/` ścieżką do Twojego projektu!

### Krok 3: Uruchom Nginx

```cmd
cd C:\nginx
start nginx
```

### Krok 4: Uruchom Django (na porcie 8000)

```cmd
cd C:\QRP_APP
venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
```

### Krok 5: Sprawdź

Otwórz w przeglądarce: `http://qrp-l9.canpack.ad` (bez portu!)

## Zarządzanie Nginx

```cmd
# Uruchom
cd C:\nginx
start nginx

# Zatrzymaj
cd C:\nginx
nginx.exe -s stop

# Restart
cd C:\nginx
nginx.exe -s reload

# Sprawdź konfigurację
cd C:\nginx
nginx.exe -t
```

## Autostart Nginx (Jako usługa Windows)

Możesz użyć NSSM do instalacji Nginx jako usługi:

```powershell
# Jako administrator
C:\nssm\win64\nssm.exe install NginxService "C:\nginx\nginx.exe"
C:\nssm\win64\nssm.exe set NginxService AppDirectory "C:\nginx"
C:\nssm\win64\nssm.exe set NginxService Start SERVICE_AUTO_START
```

## Rozwiązywanie problemów

### Problem: "Address already in use" (port 80 zajęty)

**Rozwiązanie**:
1. Sprawdź co używa portu 80:
   ```cmd
   netstat -ano | findstr :80
   ```
2. Zatrzymaj IIS lub inne usługi używające portu 80
3. Lub zmień port nginx na inny (np. 8080) i użyj w DNS

### Problem: 502 Bad Gateway

**Rozwiązanie**:
1. Upewnij się, że Django działa na porcie 8000
2. Sprawdź logi Nginx: `C:\nginx\logs\error.log`
3. Sprawdź czy `proxy_pass` wskazuje na właściwy adres

### Problem: Statyczne pliki nie ładują się

**Rozwiązanie**:
1. Zbierz statyczne pliki w Django:
   ```cmd
   python manage.py collectstatic
   ```
2. Upewnij się, że ścieżki w nginx.conf są poprawne
