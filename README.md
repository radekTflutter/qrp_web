# QRP Web (QRP_APP)

Aplikacja **Django** – rejestrator jakości (**QRP**) na stanowiskach przy liniach produkcyjnych. Operatorzy logują się (RFID lub ręcznie), rejestrują **pomiary** i **wady**, przeglądają **archiwum**; dane są zapisywane lokalnie w **SQLite** i mogą być wysyłane do **serwera centralnego** (QRP_LOCAL) przez HTTP API. Panel administracyjny służy do konfiguracji rejestratorów, linii, typów kontroli, użytkowników oraz eksportu/importu ustawień.

Szczegółowa dokumentacja techniczna (endpointy, synchronizacja, integracja z QRP_LOCAL): [`DOCUMENTACJA_QRP_SYSTEM.md`](DOCUMENTACJA_QRP_SYSTEM.md).

---

## Działanie w skrócie

| Obszar | Opis |
|--------|------|
| **Logowanie** | Strona RFID (`/`), API logowania i rejestracji kart; opcjonalnie numer KJ w zależności od rejestratora. |
| **Pomiary / wady** | Formularze z linią, typem kontroli, rodzajem testu, numerem zlecenia, zdjęciem i komentarzem. |
| **Archiwum** | Lista zapisów, filtry, eksport CSV/PDF, widok „poczekalni” rekordów niewysłanych do API. |
| **Synchronizacja** | Po zapisie oraz cyklicznie (scheduler) wysyłka do API centralnego; ponawianie przy błędach. |
| **Eksport CSV** | Opcjonalnie pliki CSV w katalogu skonfigurowanym w ustawieniach (format pod zewnętrzne systemy). |
| **Bezpieczeństwo** | Middleware: dozwolone IP (`AllowedIP`), routing po hostname/DNS do wybranej linii. |
| **Admin** | Konfiguracja całego systemu, import kart RFID z CSV/XLSX, eksport/import ustawień JSON (**bez** listy użytkowników Django w tym pliku). |

---

## Wymagania

- Python **3.10+** (zalecane 3.11 lub 3.12)
- Zależności z pliku [`requirements.txt`](requirements.txt)

---

## Instalacja lokalna

```bash
cd QRP_APP
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput   # opcjonalnie, pod produkcję
```

Uruchomienie serwera deweloperskiego:

```bash
python manage.py runserver 0.0.0.0:8000
```

- Aplikacja WWW: `http://127.0.0.1:8000/`
- Panel admina: `http://127.0.0.1:8000/admin/`

---

## Zmienne środowiskowe (opcjonalnie)

| Zmienna | Opis |
|---------|------|
| `SECRET_KEY` | Klucz Django (w produkcji **obowiązkowo** własny). |
| `DEBUG` | Konfiguracja w `qrp_project/settings.py` (domyślnie zależna od `DEBUG` w środowisku). |
| `ALLOWED_HOSTS` | Lista hostów po przecinku (domyślnie m.in. `localhost`, `127.0.0.1`). |

---

## Podmiana bazy SQLite a użytkownicy

Eksport ustawień z admina **nie** zawiera kont Django. Po wgraniu nowego pliku `db.sqlite3` możesz przenieść użytkowników i karty RFID ze starej kopii bazy:

```bash
cp db.sqlite3 db_backup.sqlite3          # kopia starej bazy
# … podmiana db.sqlite3, migrate …
python manage.py copy_users_from_db db_backup.sqlite3
```

Szczegóły: `python manage.py copy_users_from_db --help`.

---

## Publikacja w repozytorium GitHub

Repozytorium docelowe: **https://github.com/radekTflutter/qrp_web.git**

### 1. Utwórz repozytorium na GitHubie (jeśli jeszcze nie istnieje)

- Wejdź na GitHub → **New repository**.
- Nazwa np. `qrp_web`, **bez** automatycznego README (albo potem `git pull` z `--allow-unrelated-histories`, jeśli dodasz README na stronie).

### 2. Zainicjuj Git w katalogu projektu

```bash
cd /ścieżka/do/QRP_APP
git init
git add .
git commit -m "Initial commit: QRP Web (Django rejestrator QRP)"
git branch -M main
```

### 3. Połącz z GitHubem i wypchnij kod

```bash
git remote add origin https://github.com/radekTflutter/qrp_web.git
git push -u origin main
```

Przy pierwszym `git push` GitHub poprosi o logowanie (token osobisty **PAT** zamiast hasła lub **GitHub CLI**).

### 4. Jeśli repozytorium na GitHubie już ma commity (np. README utworzony na stronie)

```bash
git remote add origin https://github.com/radekTflutter/qrp_web.git
git fetch origin
git merge origin/main --allow-unrelated-histories
# rozwiąż ewentualne konflikty, potem:
git push -u origin main
```

### 5. Czego nie wysyłać do repozytorium

Plik [`.gitignore`](.gitignore) wyklucza m.in.: `db.sqlite3`, `media/`, `staticfiles/`, `.env`, wirtualne środowisko. **Nie commituj** sekretów (`SECRET_KEY`, tokeny API) – używaj zmiennych środowiskowych lub wpisów tylko lokalnie w bazie po wdrożeniu.

---

## Struktura katalogów (skrót)

| Element | Opis |
|---------|------|
| `qrp_project/` | Ustawienia Django (`settings.py`, `urls.py`, `wsgi.py`). |
| `qrp_app/` | Modele, widoki, synchronizacja, CSV, middleware, komendy `manage.py`. |
| `templates/` | Szablony admina (import ustawień itd.). |
| `static/` | Statyczne assety aplikacji. |

---

## Licencja / własność

Repozytorium i użycie zgodnie z polityką Twojej organizacji. Uzupełnij ten fragment, jeśli potrzebujesz jawnej licencji (np. MIT, własnościowa).
