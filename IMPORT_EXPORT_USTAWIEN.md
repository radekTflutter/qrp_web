# Import/Export ustawień systemowych

## Opis

Funkcjonalność importu/exportu ustawień pozwala na:
- **Eksport** wszystkich ustawień systemowych do pliku JSON
- **Import** ustawień z pliku JSON (z możliwością trybu testowego)

## Jak używać

### Eksport ustawień

1. Zaloguj się do panelu administracyjnego Django
2. Przejdź do **Qrp app** → **Ustawienia systemowe**
3. Kliknij przycisk **📥 Eksportuj ustawienia** (w prawym górnym rogu)
4. Plik JSON zostanie automatycznie pobrany z nazwą `qrp_settings_export_YYYYMMDD_HHMMSS.json`

### Import ustawień

1. Zaloguj się do panelu administracyjnego Django
2. Przejdź do **Qrp app** → **Ustawienia systemowe**
3. Kliknij przycisk **📤 Importuj ustawienia** (w prawym górnym rogu)
4. Wybierz plik JSON wyeksportowany wcześniej
5. **Zalecane:** Zaznacz "Tryb testowy" aby sprawdzić poprawność danych przed rzeczywistym importem
6. Kliknij **Importuj ustawienia**

## Co jest eksportowane/importowane?

### 1. Ustawienia systemowe (SystemSettings)
- URL API centralnego
- Token API
- Retencja danych i logów
- Ustawienia synchronizacji
- Ustawienia eksportu CSV
- Ustawienia automatycznego wylogowania
- Mapowania (linie, maszyny, rodzaje testów)

### 2. Rejestratory (Rejestrator)
- Nazwa, URL kamery, opis
- Status aktywności
- Domyślne typy kontroli i rodzaje testów
- Dostępne typy kontroli i rodzaje testów
- Ustawienie "Dla KJ"

### 3. Linie produkcyjne (LiniaProdukcyjna)
- Nazwa, URL kamery
- IP PLC
- Zmienne PLC
- Identyfikator DNS
- Status aktywności

### 4. Dozwolone adresy IP (AllowedIP)
- Adres IP
- Opis
- Status aktywności

### 5. Typy kontroli (TypKontroli)
- Nazwa, kod
- Opis
- Status aktywności
- Kolejność

### 6. Rodzaje testów (RodzajTestu)
- Nazwa, kod
- Opis
- Status aktywności
- Kolejność

### 7. Zmienne PLC (ZmiennaPLC)
- Nazwa
- Typ danych
- Wartość domyślna
- Opis

## Logika importu

### Aktualizacja vs. Tworzenie
- **Rekordy są aktualizowane** jeśli istnieją (na podstawie unikalnych pól):
  - `SystemSettings`: zawsze aktualizowany (singleton)
  - `Rejestrator`: aktualizowany po `nazwa`
  - `LiniaProdukcyjna`: aktualizowany po `nazwa` + `rejestrator`
  - `AllowedIP`: aktualizowany po `ip_address`
  - `TypKontroli`: aktualizowany po `kod`
  - `RodzajTestu`: aktualizowany po `kod`
  - `ZmiennaPLC`: aktualizowany po `nazwa`

- **Nowe rekordy są tworzone** jeśli nie istnieją

### Kolejność importu
1. **Typy kontroli** i **Rodzaje testów** (najpierw, bo są używane przez rejestratory)
2. **Rejestratory** (z przypisaniem typów kontroli i rodzajów testów)
3. **Linie produkcyjne** (wymagają rejestratorów)
4. **AllowedIP**
5. **Zmienne PLC**
6. **SystemSettings** (na końcu)

### Transakcje
- Wszystkie operacje są wykonywane w jednej transakcji
- W razie błędu wszystkie zmiany są cofane (rollback)
- Tryb testowy zawsze cofa transakcję (nic nie zapisuje)

## Tryb testowy

**Zalecane użycie:**
1. Najpierw wykonaj import w trybie testowym (zaznacz checkbox)
2. Sprawdź wyniki - liczbę utworzonych/zaktualizowanych rekordów, błędy, ostrzeżenia
3. Jeśli wszystko wygląda dobrze, wykonaj rzeczywisty import (odznacz checkbox)

## Przykładowy plik JSON

```json
{
  "version": "1.0",
  "export_date": "2024-01-15T10:30:00+01:00",
  "system_settings": {
    "api_url": "http://10.11.134.187:8000/api",
    "api_token": "your-token-here",
    "log_retention_days": 30,
    "data_retention_days": 90,
    "retry_interval_minutes": 15,
    "retry_batch_size": 10,
    "show_sync_status": true,
    "show_sync_column": true,
    "csv_export_enabled": true,
    "csv_output_path": "C:/QRP_Exports/",
    "csv_line_mapping": {"Linia 2": "C020", "Linia 3": "C030"},
    "csv_machine_mapping": {"Linia 2": "L020_PAL_01"},
    "csv_inspection_mapping": {"1": "Pokrycie lakierem..."},
    "auto_logout_enabled": true,
    "auto_logout_timeout_minutes": 5
  },
  "rejestratory": [
    {
      "nazwa": "Rejestrator 1",
      "url_kamery": "http://192.168.1.100:8080/stream",
      "opis": "Opis rejestratora",
      "aktywny": true,
      "dla_kj": true,
      "domyslny_typ_kontroli": "Standardowe",
      "domyslny_rodzaj_testu": "Pokrycie lakierem...",
      "dostepne_typy_kontroli": ["Standardowe", "Szczegółowe"],
      "dostepne_rodzaje_testu": ["Pokrycie lakierem...", "Pokrycie denka..."]
    }
  ],
  "linie_produkcyjne": [
    {
      "rejestrator_nazwa": "Rejestrator 1",
      "nazwa": "Linia 2",
      "url_kamery": "http://192.168.1.101:8080/stream",
      "ip_plc": "10.11.1.100",
      "zmienna_numer_zlecenia": "Qrp_Order_L2",
      "identyfikator_dns": "l2",
      "aktywna": true,
      "opis": "Opis linii"
    }
  ],
  "allowed_ips": [
    {
      "ip_address": "10.11.1.1",
      "opis": "Serwer główny",
      "aktywny": true
    }
  ],
  "typy_kontroli": [
    {
      "nazwa": "Standardowe",
      "kod": "STANDARD",
      "aktywny": true,
      "opis": "Standardowa kontrola",
      "kolejnosc": 1
    }
  ],
  "rodzaje_testu": [
    {
      "nazwa": "Pokrycie lakierem...",
      "kod": "1",
      "aktywny": true,
      "opis": "Test pokrycia lakierem",
      "kolejnosc": 1
    }
  ],
  "zmienne_plc": [
    {
      "nazwa": "Qrp_Order_L2",
      "typ_danych": "STRING",
      "wartosc_domyslna": "",
      "opis": "Numer zlecenia dla Linii 2"
    }
  ]
}
```

## Uwagi i ograniczenia

1. **Nie są eksportowane:**
   - Użytkownicy i karty RFID (używaj osobnej funkcji importu)
   - Pomiary i wady (dane produkcyjne)
   - Logi synchronizacji

2. **Zależności:**
   - Linie produkcyjne wymagają istniejących rejestratorów
   - Rejestratory wymagają istniejących typów kontroli i rodzajów testów (lub są tworzone podczas importu)

3. **Bezpieczeństwo:**
   - Token API jest eksportowany - zachowaj ostrożność przy udostępnianiu pliku
   - Zalecane jest użycie trybu testowego przed rzeczywistym importem

4. **Kompatybilność:**
   - Pliki eksportowane z jednej wersji systemu powinny działać z tą samą lub nowszą wersją
   - Wersja formatu jest zapisana w polu `version`

## Rozwiązywanie problemów

### Błędy podczas importu

1. **"Rejestrator 'X' nie istnieje"**
   - Upewnij się, że rejestratory są w pliku JSON przed liniami produkcyjnymi
   - Import automatycznie tworzy rejestratory, jeśli nie istnieją

2. **"Typ kontroli 'X' nie istnieje"**
   - Import automatycznie tworzy typy kontroli i rodzaje testów
   - Sprawdź czy kod jest unikalny

3. **"Nieprawidłowy format pliku JSON"**
   - Sprawdź składnię JSON (użyj walidatora online)
   - Upewnij się, że plik jest w kodowaniu UTF-8

### Ostrzeżenia

- Ostrzeżenia nie blokują importu, ale wskazują na potencjalne problemy
- Sprawdź ostrzeżenia przed wykonaniem rzeczywistego importu
