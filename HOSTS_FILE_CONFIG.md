# Konfiguracja pliku hosts dla QRP App

## Co robi plik hosts?

Plik `hosts` mapuje nazwy domenowe na adresy IP lokalnie, bez potrzeby serwera DNS.

## Konfiguracja dla testów lokalnych

### Windows

1. Otwórz Notatnik **jako administrator**
2. Otwórz plik: `C:\Windows\System32\drivers\etc\hosts`
3. Dodaj na końcu:

```
127.0.0.1    qrp-l9.canpack.ad
127.0.0.1    qrp-l2.canpack.ad
```

4. Zapisz plik

### Linux/macOS

```bash
sudo nano /etc/hosts
```

Dodaj:
```
127.0.0.1    qrp-l9.canpack.ad
127.0.0.1    qrp-l2.canpack.ad
```

## Co to rozwiązuje?

✅ **Działa lokalnie**: `http://qrp-l9.canpack.ad:8000` będzie rozwiązywane na `127.0.0.1:8000`

## Czego NIE rozwiązuje?

❌ **Nadal potrzebujesz portu**: Musisz używać `http://qrp-l9.canpack.ad:8000` (z `:8000`)

❌ **Nie działa na innych komputerach**: Plik hosts działa tylko na komputerze, na którym go zmodyfikujesz

## Rozwiązania

### Opcja 1: Tylko plik hosts (z portem)

**Dla testów lokalnych wystarczy:**
- Plik hosts + Django na `0.0.0.0:8000`
- Dostęp: `http://qrp-l9.canpack.ad:8000`

**Korzyści:**
- ✅ Szybka konfiguracja
- ✅ Działa lokalnie
- ✅ Nie potrzeba Nginx/IIS

**Ograniczenia:**
- ❌ Nadal trzeba podawać port `:8000`
- ❌ Nie działa z innych komputerów w sieci

### Opcja 2: Plik hosts + Nginx (bez portu)

**Dla lokalnych testów bez portu:**
- Plik hosts + Nginx na porcie 80 + Django na porcie 8000
- Dostęp: `http://qrp-l9.canpack.ad` (bez portu!)

**Korzyści:**
- ✅ URL bez portu
- ✅ Działa lokalnie

**Ograniczenia:**
- ❌ Wymaga Nginx
- ❌ Nie działa z innych komputerów (chyba że zmienisz IP w hosts na IP sieciowe)

### Opcja 3: DNS w sieci (produkcja)

**Dla całej sieci:**
- Konfiguracja DNS w Active Directory
- Nginx na porcie 80 (opcjonalnie, jeśli chcemy bez portu)
- Django na porcie 8000

**Korzyści:**
- ✅ Działa na wszystkich komputerach w sieci
- ✅ Może działać bez portu (z Nginx)

## Rekomendacja

### Dla testów lokalnych:

**Wystarczy plik hosts:**
```
127.0.0.1    qrp-l9.canpack.ad
```

Uruchom Django:
```bash
python manage.py runserver 0.0.0.0:8000
```

Dostęp: `http://qrp-l9.canpack.ad:8000`

### Dla produkcji (sieć lokalna):

**Z Nginx (bez portu):**
1. Skonfiguruj DNS w Active Directory (zamiast pliku hosts)
2. Zainstaluj Nginx jako usługę
3. Zainstaluj Django jako usługę

**Bez Nginx (z portem):**
1. Skonfiguruj DNS w Active Directory
2. Zainstaluj Django jako usługę
3. Dostęp: `http://qrp-l9.canpack.ad:8000`

## Porównanie

| Rozwiązanie | Plik hosts | DNS sieciowy | Port w URL | Działa sieciowo |
|-------------|------------|--------------|------------|-----------------|
| **Hosts tylko** | ✅ | ❌ | ✅ (`:8000`) | ❌ |
| **Hosts + Nginx** | ✅ | ❌ | ❌ | ❌ |
| **DNS + Django** | ❌ | ✅ | ✅ (`:8000`) | ✅ |
| **DNS + Nginx** | ❌ | ✅ | ❌ | ✅ |

## Szybka konfiguracja dla testów

### Windows:

1. Edytuj `C:\Windows\System32\drivers\etc\hosts` (jako administrator):
   ```
   127.0.0.1    qrp-l9.canpack.ad
   127.0.0.1    qrp-l2.canpack.ad
   ```

2. Uruchom Django:
   ```cmd
   python manage.py runserver 0.0.0.0:8000
   ```

3. Otwórz w przeglądarce:
   ```
   http://qrp-l9.canpack.ad:8000
   ```

**To wystarczy do lokalnych testów!**

## Weryfikacja

```cmd
# Sprawdź czy hosts działa
ping qrp-l9.canpack.ad

# Powinien pokazać: Reply from 127.0.0.1
```

## Uwagi

- Plik hosts ma priorytet nad DNS, więc jeśli masz wpis w hosts, nie będzie używał DNS sieciowego
- Aby wyczyścić cache DNS w Windows: `ipconfig /flushdns`
- W produkcji użyj DNS w Active Directory zamiast pliku hosts
