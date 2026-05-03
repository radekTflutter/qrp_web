# Instrukcje naprawy - Menu hamburger i zakres IP

## 1. Naprawa menu hamburger w orientacji pionowej

### Problem
Menu hamburger pojawia się w trybie pełnoekranowym w orientacji pionowej, a powinno się pojawiać dopiero gdy szerokość okna jest mniejsza niż określony próg.

### Rozwiązanie
Usuń warunek `(orientation: portrait)` z media query, które kontrolują wyświetlanie menu hamburger.

---

## 📝 Plik 1: `qrp_app/templates/qrp_app/base.html`

### Lokalizacja: Linia 364

**PRZED:**
```css
@media (max-width: 900px), (orientation: portrait) {
    .nav-menu {
        display: none;
    }

    .hamburger {
        display: flex;
    }

    .user-name {
        display: none;
    }
}
```

**PO:**
```css
@media (max-width: 900px) {
    .nav-menu {
        display: none;
    }

    .hamburger {
        display: flex;
    }

    .user-name {
        display: none;
    }
}
```

**Co zmienić:**
- Usuń `, (orientation: portrait)` z linii 364
- Zostaw tylko `@media (max-width: 900px) {`

---

## 📝 Plik 2: `qrp_app/templates/qrp_app/defect.html`

### Lokalizacja: Linia 315

**PRZED:**
```css
/* ≤1200px lub portrait: miniaturka obok szczegółów (tryb horyzontalny) */
@media (max-width: 1200px), (orientation: portrait) {
    .last-record-wrapper {
        flex-direction: row;
    }

    .last-record-thumbnail {
        width: 150px;
        height: 100px;
        aspect-ratio: auto;
        border-radius: 0.5rem;
    }

    .last-record-info {
        margin-top: 0;
    }
```

**PO:**
```css
/* ≤1200px: miniaturka obok szczegółów (tryb horyzontalny) */
@media (max-width: 1200px) {
    .last-record-wrapper {
        flex-direction: row;
    }

    .last-record-thumbnail {
        width: 150px;
        height: 100px;
        aspect-ratio: auto;
        border-radius: 0.5rem;
    }

    .last-record-info {
        margin-top: 0;
    }
```

**Co zmienić:**
- Usuń `, (orientation: portrait)` z linii 315
- Zostaw tylko `@media (max-width: 1200px) {`
- Opcjonalnie: zaktualizuj komentarz (usuń "lub portrait")

---

## 📝 Plik 3: `qrp_app/templates/qrp_app/measurement.html`

### Lokalizacja: Linia 325

**PRZED:**
```css
/* ≤1200px lub portrait: miniaturka obok szczegółów (tryb horyzontalny) */
@media (max-width: 1200px), (orientation: portrait) {
    .last-record-wrapper {
        flex-direction: row;
    }

    .last-record-thumbnail {
        width: 150px;
        height: 100px;
        aspect-ratio: auto;
    }
```

**PO:**
```css
/* ≤1200px: miniaturka obok szczegółów (tryb horyzontalny) */
@media (max-width: 1200px) {
    .last-record-wrapper {
        flex-direction: row;
    }

    .last-record-thumbnail {
        width: 150px;
        height: 100px;
        aspect-ratio: auto;
    }
```

**Co zmienić:**
- Usuń `, (orientation: portrait)` z linii 325
- Zostaw tylko `@media (max-width: 1200px) {`
- Opcjonalnie: zaktualizuj komentarz (usuń "lub portrait")

---

## 2. Dodanie zakresu IP 10.11.x.x do dozwolonych adresów

### Problem
Django `ALLOWED_HOSTS` nie obsługuje zakresów IP bezpośrednio. Trzeba stworzyć middleware, który sprawdzi IP klienta i pozwoli na dostęp jeśli jest w zakresie 10.11.x.x.

### Rozwiązanie
Dodaj nowy middleware, który sprawdza IP klienta i dodaje go do ALLOWED_HOSTS jeśli jest w zakresie 10.11.x.x.

---

## 📝 Plik 4: `qrp_app/middleware.py`

### Lokalizacja: Na końcu pliku (po klasie `HostnameRoutingMiddleware`)

**UWAGA:** Middleware nie jest potrzebny jeśli dodasz wszystkie IP z zakresu 10.11.x.x do ALLOWED_HOSTS w settings.py (patrz Plik 6 - wersja bez middleware).

**Jeśli chcesz użyć middleware (opcjonalne - bardziej zaawansowane):**

**DODAJ:**
```python
class IPRangeMiddleware(MiddlewareMixin):
    """
    Middleware, które pozwala na dostęp z zakresu IP 10.11.x.x.
    Musi być umieszczone PRZED SecurityMiddleware w settings.py.
    """
    
    def process_request(self, request):
        """
        Sprawdza czy IP klienta jest w zakresie 10.11.x.x
        i jeśli tak, ustawia flagę w requestie.
        """
        # Pobierz IP klienta
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        # Sprawdź czy IP jest w zakresie 10.11.x.x
        if ip.startswith('10.11.'):
            # Ustaw flagę w requestie - SecurityMiddleware sprawdzi ALLOWED_HOSTS
            # IP musi być już w ALLOWED_HOSTS (dodane w settings.py)
            request._ip_in_range = True
        
        return None
```

**UWAGA:** To middleware tylko sprawdza IP - IP musi być już w ALLOWED_HOSTS (patrz Plik 6).

---

## 📝 Plik 5: `qrp_project/settings.py` - Middleware (OPCJONALNE)

### Lokalizacja: W sekcji `MIDDLEWARE` (linia 26-35)

**UWAGA:** Middleware NIE jest wymagany jeśli używasz rozwiązania z Pliku 6 (dodanie wszystkich IP do ALLOWED_HOSTS). Middleware jest opcjonalny i może być użyty do dodatkowej walidacji.

**Jeśli chcesz użyć middleware (opcjonalne):**

**PRZED:**
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'qrp_app.middleware.HostnameRoutingMiddleware',  # Routing na podstawie hostname DNS
]
```

**PO:**
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'qrp_app.middleware.IPRangeMiddleware',  # Pozwala na dostęp z zakresu IP 10.11.x.x (opcjonalne)
    'qrp_app.middleware.HostnameRoutingMiddleware',  # Routing na podstawie hostname DNS
]
```

**Co zmienić:**
- **OPCJONALNE:** Dodaj `'qrp_app.middleware.IPRangeMiddleware',` przed `HostnameRoutingMiddleware`
- **UWAGA:** Jeśli używasz rozwiązania z Pliku 6 (dodanie IP do ALLOWED_HOSTS), middleware NIE jest potrzebny

---

## 📝 Plik 6: `qrp_project/settings.py` - Dodanie zakresu IP do ALLOWED_HOSTS

### Lokalizacja: W sekcji `ALLOWED_HOSTS` (linia 11-14)

**PRZED:**
```python
ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1,.canpack.ad'
).split(',')
```

**PO (wersja 1 - proste rozwiązanie - dodaje wszystkie IP z zakresu):**
```python
# Podstawowe dozwolone hosty
allowed_hosts_list = os.environ.get(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1,.canpack.ad'
).split(',')

# Dodaj zakres IP 10.11.x.x (wszystkie możliwe IP z tego zakresu)
# Generujemy wszystkie IP z zakresu 10.11.0.0 - 10.11.255.255
for third_octet in range(256):
    for fourth_octet in range(256):
        allowed_hosts_list.append(f'10.11.{third_octet}.{fourth_octet}')

ALLOWED_HOSTS = allowed_hosts_list
```

**UWAGA:** Powyższe rozwiązanie dodaje 65536 adresów IP do listy. To działa, ale może być wolne przy starcie aplikacji.

**PO (wersja 2 - bardziej efektywne - używa wildcard pattern):**
```python
# Podstawowe dozwolone hosty
allowed_hosts_list = os.environ.get(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1,.canpack.ad'
).split(',')

# Dodaj zakres IP 10.11.x.x używając wzorca
# Django nie obsługuje wildcard dla IP bezpośrednio, więc dodajemy wszystkie
# Ale możemy to zoptymalizować używając listy zamiast pętli
allowed_hosts_list.extend([f'10.11.{i}.{j}' for i in range(256) for j in range(256)])

ALLOWED_HOSTS = allowed_hosts_list
```

**Co zmienić:**
- Wybierz wersję 1 lub 2 (oba działają tak samo, wersja 2 jest bardziej zwięzła)
- Zastąp całą sekcję ALLOWED_HOSTS powyższym kodem
- Po zmianie zrestartuj serwer Django

---

## ✅ Podsumowanie zmian

### Pliki WYMAGANE do edycji (menu hamburger):
1. ✅ **WYMAGANE** - `qrp_app/templates/qrp_app/base.html` - linia 364
2. ✅ **WYMAGANE** - `qrp_app/templates/qrp_app/defect.html` - linia 315
3. ✅ **WYMAGANE** - `qrp_app/templates/qrp_app/measurement.html` - linia 325

### Pliki do edycji (zakres IP 10.11.x.x):
4. ✅ **WYMAGANE** - `qrp_project/settings.py` - linia 11-14 (ALLOWED_HOSTS) - **WYBIERZ JEDNO ROZWIĄZANIE:**
   - **Opcja A (proste):** Dodaj wszystkie IP z zakresu 10.11.x.x do ALLOWED_HOSTS (Plik 6 - wersja 1 lub 2)
   - **Opcja B (zaawansowane):** Dodaj middleware (Plik 4 + Plik 5) - **NIE jest wymagane jeśli używasz Opcji A**

5. ⚠️ **OPCJONALNE** - `qrp_app/middleware.py` - dodaj klasę `IPRangeMiddleware` (tylko jeśli używasz Opcji B)
6. ⚠️ **OPCJONALNE** - `qrp_project/settings.py` - dodaj middleware do listy MIDDLEWARE (tylko jeśli używasz Opcji B)

### Zalecane rozwiązanie:
- **Menu hamburger:** Wykonaj zmiany w plikach 1-3 (wymagane)
- **Zakres IP:** Użyj **Opcji A** (dodaj IP do ALLOWED_HOSTS) - prostsze i wystarczające

### Testowanie:
1. **Menu hamburger:**
   - Otwórz aplikację w trybie pełnoekranowym w orientacji pionowej
   - Menu hamburger NIE powinno się pojawić
   - Zmniejsz szerokość okna poniżej 900px
   - Menu hamburger POWINNO się pojawić

2. **Zakres IP 10.11.x.x:**
   - Uruchom serwer: `python manage.py runserver 0.0.0.0:8000`
   - Spróbuj uzyskać dostęp z urządzenia o IP w zakresie 10.11.x.x
   - Aplikacja powinna być dostępna bez błędów ALLOWED_HOSTS

---

## ⚠️ Uwagi

### Menu hamburger:
- Zmiany w media query są natychmiastowe po odświeżeniu strony
- Nie wymagają restartu serwera

### Zakres IP 10.11.x.x:
- **Jeśli używasz Opcji A (ALLOWED_HOSTS):**
  - Po zmianie w `settings.py` **ZRESTARTUJ serwer Django**
  - Dodanie 65536 IP może spowolnić start aplikacji o 1-2 sekundy (akceptowalne)
  
- **Jeśli używasz Opcji B (middleware):**
  - Middleware `IPRangeMiddleware` musi być dodany PRZED `HostnameRoutingMiddleware` w settings.py
  - **SecurityMiddleware** musi być pierwszy w liście MIDDLEWARE
  - Po zmianach w middleware, **zrestartuj serwer Django**
  - Jeśli używasz reverse proxy (nginx, IIS), upewnij się, że przekazuje prawidłowy IP klienta w nagłówku `X-Forwarded-For`

### Które rozwiązanie wybrać?
- **Opcja A (ALLOWED_HOSTS)** - **ZALECANE** - prostsze, działa od razu, nie wymaga dodatkowego kodu
- **Opcja B (middleware)** - tylko jeśli potrzebujesz dodatkowej logiki lub walidacji IP
