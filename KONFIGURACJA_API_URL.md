# Konfiguracja URL API dla serwera głównego

## Ustawienia w panelu admin

W panelu administracyjnym rejestratora (`/admin/`) w sekcji **Ustawienia systemowe** należy ustawić:

### URL API centralnego
**Wartość:** `http://10.11.1.1:8000/api`

⚠️ **UWAGA:** 
- Podaj **bazowy URL** bez końcowej ścieżki (`/measurements/` lub `/defects/`)
- System automatycznie doda odpowiednią ścieżkę w zależności od typu rekordu
- Upewnij się, że URL nie kończy się na `/` (system automatycznie go usunie)

### Token API
**Wartość:** Token autoryzacji (jeśli wymagany przez serwer główny)

## Endpointy serwera głównego

Serwer główny (QRP_LOCAL/local_project) ma następujące endpointy:

### 1. Pomiary
- **URL:** `http://10.11.1.1:8000/api/measurements/`
- **Metoda:** `POST`
- **Content-Type:** `application/json` lub `multipart/form-data` (gdy jest zdjęcie)

### 2. Wady
- **URL:** `http://10.11.1.1:8000/api/defects/`
- **Metoda:** `POST`
- **Content-Type:** `application/json` lub `multipart/form-data` (gdy jest zdjęcie)

### 3. Health Check
- **URL:** `http://10.11.1.1:8000/api/health/`
- **Metoda:** `GET`
- **Użycie:** Sprawdzenie czy serwer działa

## Jak działa routing

W pliku `qrp_app/sync_service.py`:

1. Pobiera `api_url` z `SystemSettings` (np. `http://10.11.1.1:8000/api`)
2. Usuwa końcowy `/` jeśli istnieje
3. Dodaje odpowiednią ścieżkę:
   - Dla `Pomiar`: `/measurements/`
   - Dla `Wada`: `/defects/`
4. Wysyła żądanie na pełny URL (np. `http://10.11.1.1:8000/api/measurements/`)

## Przykłady konfiguracji

### Przykład 1: Serwer lokalny
```
URL API centralnego: http://localhost:8000/api
Token API: (puste lub token)
```

### Przykład 2: Serwer na sieci
```
URL API centralnego: http://10.11.1.1:8000/api
Token API: (puste lub token)
```

### Przykład 3: Serwer z domeną
```
URL API centralnego: http://qrp-server.canpack.ad/api
Token API: (puste lub token)
```

## Weryfikacja konfiguracji

1. Ustaw `api_url` w panelu admin
2. Utwórz testowy pomiar lub wadę
3. Sprawdź logi synchronizacji w `/admin/qrp_app/synclog/`
4. Sprawdź logi API na serwerze głównym w `/admin/api/apirequestlog/`

## Rozwiązywanie problemów

### Błąd: "API centralne nie jest skonfigurowane"
- Sprawdź czy `api_url` jest ustawione w panelu admin
- Sprawdź czy `api_token` jest ustawione (jeśli wymagane)

### Błąd: "Błąd połączenia z API centralnym"
- Sprawdź czy serwer główny jest uruchomiony
- Sprawdź czy URL jest poprawny (bez `/measurements/` na końcu)
- Sprawdź połączenie sieciowe między rejestratorem a serwerem głównym

### Błąd: "Błąd HTTP 404"
- Sprawdź czy endpoint istnieje na serwerze głównym
- Sprawdź czy URL jest poprawny (powinien być `http://.../api` bez końcowej ścieżki)

### Błąd: "Błąd HTTP 401/403"
- Sprawdź czy token API jest poprawny
- Sprawdź czy serwer główny wymaga autoryzacji
