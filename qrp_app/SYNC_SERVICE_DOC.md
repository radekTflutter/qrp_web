# Dokumentacja: sync_service.py

## Lokalizacja pliku
**`qrp_app/sync_service.py`**

## Opis
Plik zawiera funkcję `send_to_central_api()`, która wysyła dane z pomiarów i wad z rejestratorów do serwera głównego (QRP_LOCAL/local_project).

## Główna funkcja

### `send_to_central_api(instance: Pomiar | Wada) -> bool`

Wysyła pojedynczy rekord (Pomiar lub Wada) do centralnego API.

**Parametry:**
- `instance`: Instancja modelu `Pomiar` lub `Wada` do wysłania

**Zwraca:**
- `True` jeśli synchronizacja się powiodła
- `False` w przeciwnym razie

**Proces:**
1. Pobiera ustawienia systemowe z `SystemSettings`
2. Sprawdza czy API jest skonfigurowane (`api_url` i `api_token`)
3. Przygotowuje dane do wysłania (`_prepare_data()`)
4. Przygotowuje pliki (zdjęcia) do wysłania (`_prepare_files()`)
5. Wysyła żądanie HTTP POST do serwera głównego
6. Aktualizuje status synchronizacji w rekordzie (`is_synced`, `synced_at`)
7. Loguje wynik do `SyncLog`

## Format danych

### Dla Pomiar:
```json
{
  "record_id": 123,
  "record_type": "measurement",
  "line_name": "Linia 2",
  "line_id": 2,
  "user": "jan.kowalski",
  "order_number": "ORD-2024-001",
  "control_type": "Standardowe",
  "test_type": "1",
  "test_type_display": "Pokrycie lakierem...",
  "comment": "Komentarz",
  "created_at": "2024-01-15T10:30:00+01:00"
}
```

### Dla Wada:
```json
{
  "record_id": 456,
  "record_type": "defect",
  "line_name": "Linia 2",
  "line_id": 2,
  "user": "jan.kowalski",
  "order_number": "ORD-2024-001",
  "control_type": "Standardowe",
  "defect_description": "Opis wady",
  "comment": "Dodatkowe uwagi",
  "created_at": "2024-01-15T10:30:00+01:00"
}
```

## Wysyłanie danych

### Bez zdjęcia (tylko JSON):
```python
POST /api/measurements/
Content-Type: application/json
Authorization: Bearer {token}

{
  "record_id": 123,
  "line_name": "Linia 2",
  ...
}
```

### Ze zdjęciem (multipart/form-data):
```python
POST /api/measurements/
Content-Type: multipart/form-data
Authorization: Bearer {token}

data: {"record_id": 123, "line_name": "Linia 2", ...}
photo: [plik zdjęcia]
```

## Konfiguracja

Ustawienia API są przechowywane w modelu `SystemSettings`:
- `api_url` - URL serwera głównego (np. `http://10.11.1.1:8000/api/measurements/`)
- `api_token` - Token autoryzacji (Bearer token)

## Użycie

Funkcja jest wywoływana automatycznie w:
1. **`views.py`** - `MeasurementAPI.post()` i `DefectAPI.post()` - po zapisaniu rekordu
2. **`management/commands/sync_records.py`** - komenda do synchronizacji zaległych rekordów
3. **`views.py`** - `SyncNowAPI.post()` - ręczna synchronizacja

## Endpointy serwera głównego

- **Pomiary**: `POST /api/measurements/`
- **Wady**: `POST /api/defects/`
- **Health check**: `GET /api/health/`

## Obsługa błędów

Funkcja loguje wszystkie błędy do:
- `SyncLog` model (baza danych)
- Logger Django (`logger.error()`)

Typy błędów:
- Brak konfiguracji API
- Błąd przygotowania danych
- Timeout połączenia
- Błąd HTTP (4xx, 5xx)
- Błąd połączenia sieciowego
- Ogólne błędy

## Uwagi

1. **Nie blokuje zapisu rekordu** - jeśli synchronizacja się nie powiedzie, rekord i tak zostaje zapisany lokalnie
2. **Timeout**: 30 sekund (`REQUEST_TIMEOUT`)
3. **Zdjęcia**: Wysyłane jako pliki binarne w multipart/form-data
4. **Daty**: Konwertowane na lokalną strefę czasową (Europe/Warsaw) przed wysłaniem
5. **Token**: Wymagany w nagłówku `Authorization: Bearer {token}`
