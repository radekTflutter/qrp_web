# QRP Web (QRP_APP)

**Django** web application – a quality **QRP** station recorder for production lines. Operators sign in (RFID or manually), register **measurements** and **defects**, browse the **archive**; data is stored locally in **SQLite** and can be sent to a **central server** (QRP_LOCAL) over HTTP API. The Django admin is used to configure registrars, lines, control types, users, and JSON settings export/import.

Technical reference (endpoints, sync, QRP_LOCAL integration): [`DOCUMENTATION_QRP_SYSTEM.md`](DOCUMENTATION_QRP_SYSTEM.md).

---

## Overview

| Area | Description |
|------|-------------|
| **Sign-in** | RFID page (`/`), login and card registration APIs; optional KJ number depending on registrar settings. |
| **Measurements / defects** | Forms with line, control type, test type, work order number, photo, and comment. |
| **Archive** | Record list, filters, CSV/PDF export, “pending queue” for records not yet sent to the API. |
| **Synchronisation** | After save and on a schedule (background scheduler) to the central API; retries on errors. |
| **CSV export** | Optional CSV files in a configured folder (format for downstream systems). |
| **Security** | Middleware: allowed IPs (`AllowedIP`), hostname/DNS routing to the selected line. |
| **Admin** | Full system configuration, RFID card import from CSV/XLSX, JSON settings export/import (**does not** include the Django user list in that file). |

---

## Requirements

- Python **3.10+** (3.11 or 3.12 recommended)
- Dependencies from [`requirements.txt`](requirements.txt)

---

## Local setup

```bash
cd QRP_APP
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput   # optional, for production-style static files
```

Run the development server:

```bash
python manage.py runserver 0.0.0.0:8000
```

- Web app: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

---

## Environment variables (optional)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key (use your **own** value in production). |
| `DEBUG` | Controlled in `qrp_project/settings.py` (depends on the `DEBUG` environment variable by default). |
| `ALLOWED_HOSTS` | Comma-separated host list (defaults include `localhost`, `127.0.0.1`). |

---

## Replacing the SQLite database and keeping users

Admin settings export **does not** include Django user accounts. After replacing `db.sqlite3`, you can copy users and RFID cards from a backup of the old database:

```bash
cp db.sqlite3 db_backup.sqlite3          # backup of old DB
# … replace db.sqlite3, run migrate …
python manage.py copy_users_from_db db_backup.sqlite3
```

See: `python manage.py copy_users_from_db --help`.

---

## Publishing to GitHub

Target repository: **https://github.com/radekTflutter/qrp_web.git**

### 1. Create the GitHub repository (if it does not exist yet)

- GitHub → **New repository**.
- Name e.g. `qrp_web`, **without** auto-generated README (or later use `git pull` with `--allow-unrelated-histories` if you add a README on the website).

### 2. Initialise Git in the project folder

```bash
cd /path/to/QRP_APP
git init
git add .
git commit -m "Initial commit: QRP Web (Django QRP station)"
git branch -M main
```

### 3. Add the remote and push

```bash
git remote add origin https://github.com/radekTflutter/qrp_web.git
git push -u origin main
```

The first `git push` usually requires authentication (a **personal access token** instead of a password, or **GitHub CLI**).

### 4. If the remote already has commits (e.g. README created on GitHub)

```bash
git remote add origin https://github.com/radekTflutter/qrp_web.git
git fetch origin
git merge origin/main --allow-unrelated-histories
# resolve any conflicts, then:
git push -u origin main
```

### 5. What not to commit

[`.gitignore`](.gitignore) excludes e.g. `db.sqlite3`, `media/`, `staticfiles/`, `.env`, virtual environments. **Do not commit** secrets (`SECRET_KEY`, API tokens) – use environment variables or configure secrets only after deployment.

---

## Directory layout (short)

| Path | Description |
|------|-------------|
| `qrp_project/` | Django project settings (`settings.py`, `urls.py`, `wsgi.py`). |
| `qrp_app/` | Models, views, sync, CSV, middleware, `manage.py` commands. |
| `templates/` | Admin templates (settings import, etc.). |
| `static/` | Application static assets. |

---

## License / ownership

Repository use is subject to your organisation’s policy. Add an explicit licence here if needed (e.g. MIT, proprietary).
