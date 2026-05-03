# Konfiguracja dla serwera głównego na 10.11.134.187:8000

## 1. Konfiguracja w rejestratorach (QRP_APP)

### Panel Admin → Ustawienia systemowe

1. Zaloguj się do panelu admin rejestratora: `http://[adres_rejestratora]/admin/`
2. Przejdź do: **Ustawienia systemowe** (SystemSettings)
3. Ustaw następujące wartości:

   **URL API centralnego:** `http://10.11.134.187:8000/api`
   
   **Token API:** (opcjonalnie, jeśli wymagany przez serwer główny)

4. Zapisz ustawienia

### Automatyczne endpointy

Po zapisaniu, rejestrator będzie automatycznie wysyłał dane na:
- **Pomiary:** `http://10.11.134.187:8000/api/measurements/`
- **Wady:** `http://10.11.134.187:8000/api/defects/`

## 2. Konfiguracja w serwerze głównym (QRP_LOCAL/local_project)

### A. Ustawienia ALLOWED_HOSTS

✅ **Już zaktualizowane w `local_project/settings.py`:**
```python
ALLOWED_HOSTS = ['10.11.134.187', 'localhost', '127.0.0.1', '10.11.*']
```

### B. Uruchomienie serwera

Uruchom serwer na wszystkich interfejsach (0.0.0.0):
```bash
cd /Users/radoslawtota/Development/QRP/QRP_LOCAL/local_project
python manage.py runserver 0.0.0.0:8000
```

Lub jeśli chcesz nasłuchiwać tylko na konkretnym adresie IP:
```bash
python manage.py runserver 10.11.134.187:8000
```

## 3. Weryfikacja konfiguracji

### Test z rejestratora (lub innego komputera w sieci):

```bash
# Test health check
curl http://10.11.134.187:8000/api/health/

# Oczekiwana odpowiedź:
# {"status": "ok", "timestamp": "2024-01-15T10:30:00+01:00"}
```

### Test endpoint pomiarów:

```bash
curl -X POST http://10.11.134.187:8000/api/measurements/10/ \
  -H "Content-Type: application/json" \
  -d '{
    "line_name": "Test",
    "control_type": "Standardowe",
    "test_type": "1",
    "created_at": "2024-01-15T10:30:00+01:00"
  }'
```

## 4. Sprawdzenie logów

### W serwerze głównym:

1. **Logi API:** `/admin/api/apirequestlog/` - wszystkie żądania
2. **Pomiary:** `/admin/api/pomiar/` - zapisane pomiary
3. **Wady:** `/admin/api/wada/` - zapisane wady

### W rejestratorze:

1. **Logi synchronizacji:** `/admin/qrp_app/synclog/` - status synchronizacji

## 5. Rozwiązywanie problemów

### Błąd: "DisallowedHost at /api/..."
**Rozwiązanie:**
- Sprawdź czy `ALLOWED_HOSTS` w `settings.py` zawiera `10.11.134.187`
- Zrestartuj serwer Django

### Błąd: "Connection refused"
**Rozwiązanie:**
- Sprawdź czy serwer jest uruchomiony: `python manage.py runserver 0.0.0.0:8000`
- Sprawdź firewall - port 8000 musi być otwarty
- Sprawdź czy serwer nasłuchuje na wszystkich interfejsach (0.0.0.0)

### Błąd: "Timeout"
**Rozwiązanie:**
- Sprawdź połączenie sieciowe między rejestratorem a serwerem
- Sprawdź czy nie ma blokady firewall
- Sprawdź czy port 8000 jest dostępny: `telnet 10.11.134.187 8000`

### Błąd: "404 Not Found"
**Rozwiązanie:**
- Sprawdź czy URL w rejestratorze to: `http://10.11.134.187:8000/api` (bez końcowej ścieżki)
- Sprawdź czy serwer główny jest uruchomiony
- Sprawdź logi w `/admin/api/apirequestlog/`

## 6. Podsumowanie konfiguracji

### Rejestratory:
```
URL API centralnego: http://10.11.134.187:8000/api
```

### Serwer główny:
```
ALLOWED_HOSTS: ['10.11.134.187', 'localhost', '127.0.0.1', '10.11.*']
Uruchomienie: python manage.py runserver 0.0.0.0:8000
```

### Endpointy:
```
Pomiary: POST http://10.11.134.187:8000/api/measurements/
Wady:    POST http://10.11.134.187:8000/api/defects/
Health:  GET  http://10.11.134.187:8000/api/health/
```
