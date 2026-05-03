# QRP Control System - Szybki Start

## 🚀 Instalacja w 5 krokach

### 1. Zainstaluj zależności
```bash
pip install -r requirements.txt
```

### 2. Utwórz migracje
```bash
python manage.py makemigrations
```

### 3. Zastosuj migracje
```bash
python manage.py migrate
```

### 4. Utwórz superużytkownika
```bash
python manage.py createsuperuser
```

### 5. Uruchom serwer
```bash
python manage.py runserver
```

Otwórz w przeglądarce: **http://localhost:8000/admin/**

---

## 📋 Jak używać panelu administracyjnego

### Krok 1: Dodaj Rejestrator
1. Przejdź do sekcji **Rejestratory**
2. Kliknij **"Dodaj rejestrator"**
3. Wypełnij:
   - **Nazwa**: np. "Rejestrator Hala A"
   - **Opis**: (opcjonalnie)
   - **Aktywny**: ✓
4. Zapisz

### Krok 2: Dodaj Linię Produkcyjną
1. W edycji rejestratora, w sekcji **"Linie produkcyjne"** kliknij **"Dodaj kolejną Linia produkcyjna"**
2. Wypełnij:
   - **Nazwa**: np. "Linia 2"
   - **URL kamery**: np. `http://192.168.1.100:8080/stream`
   - **IP PLC**: np. `192.168.1.50`
   - **Port PLC**: `502` (domyślnie)
   - **Aktywna**: ✓
3. Zapisz

### Krok 3: Dodaj Zmienne PLC
1. W edycji linii produkcyjnej, w sekcji **"Zmienne PLC"** kliknij **"Dodaj kolejną Zmienna PLC"**
2. Wypełnij dla każdej zmiennej:
   - **Nazwa**: np. "Temperatura"
   - **Adres PLC**: np. `DB1.DBD0`
   - **Typ danych**: wybierz z listy (BOOL, INT, DINT, REAL, STRING)
   - **Jednostka**: np. `°C`
   - **Wartość min**: (opcjonalnie)
   - **Wartość max**: (opcjonalnie)
   - **Kolejność**: `0` (mniejsza wartość = wyżej na liście)
   - **Aktywna**: ✓
3. Zapisz

---

## 🎯 Przykładowa struktura

```
Rejestrator: "Rejestrator Hala A"
  └── Linia: "Linia 2"
      ├── URL kamery: http://192.168.1.100:8080/stream
      ├── IP PLC: 192.168.1.50
      └── Zmienne PLC:
          ├── Temperatura (DB1.DBD0, REAL, °C)
          ├── Ciśnienie (DB1.DBD4, REAL, bar)
          └── Status (I0.0, BOOL)
```

---

## 💡 Wskazówki

- **Rejestrator** może mieć wiele **Linii produkcyjnych**
- **Linia produkcyjna** może mieć wiele **Zmiennych PLC**
- Wszystkie pola z datami są automatycznie wypełniane
- Możesz filtrować i wyszukiwać w każdej sekcji
- Statystyki są wyświetlane automatycznie w panelu rejestratora

---

## 🔧 Rozwiązywanie problemów

### Problem: "ModuleNotFoundError: No module named 'django'"
**Rozwiązanie**: Zainstaluj Django: `pip install -r requirements.txt`

### Problem: Migracje nie działają
**Rozwiązanie**: Upewnij się, że jesteś w katalogu projektu i Django jest zainstalowane

### Problem: Nie widzę panelu administracyjnego
**Rozwiązanie**: Upewnij się, że:
1. Serwer działa (`python manage.py runserver`)
2. Jesteś zalogowany jako superużytkownik
3. Adres to: `http://localhost:8000/admin/`

---

## 📞 Wsparcie

Wszystkie modele są w pełni zintegrowane z panelem administracyjnym Django.
Wszystkie pola są walidowane i zabezpieczone przed błędami.

