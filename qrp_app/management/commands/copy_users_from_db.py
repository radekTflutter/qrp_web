"""
Kopiuje użytkowników (auth.User) i karty RFID ze starej bazy SQLite do aktualnej.
Użycie gdy podmieniasz plik bazy na nowy i chcesz przenieść istniejących użytkowników.

  python manage.py copy_users_from_db /ścieżka/do/starej_bazy.sqlite3

Opcja --dry-run tylko pokaże, ilu użytkowników i kart zostanie skopiowanych.
"""
import sqlite3
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from qrp_app.models import RFIDCard


def _parse_sqlite_datetime(value):
    """Zamienia string daty z SQLite na timezone-aware datetime lub zwraca None."""
    if value is None or value == '':
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Kopiuje użytkowników i karty RFID ze starej bazy SQLite do aktualnej (np. po podmianie pliku bazy).'

    def add_arguments(self, parser):
        parser.add_argument(
            'old_db_path',
            type=str,
            help='Ścieżka do pliku starej bazy SQLite (np. /backup/db_old.sqlite3)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Pokaż tylko podsumowanie, bez zapisu',
        )

    def handle(self, *args, **options):
        old_db_path = options['old_db_path']
        dry_run = options['dry_run']

        try:
            conn = sqlite3.connect(old_db_path)
            conn.row_factory = sqlite3.Row
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Nie można otworzyć starej bazy: {old_db_path}. Błąd: {e}'))
            return

        try:
            # Odczyt użytkowników ze starej bazy
            cur = conn.execute(
                'SELECT id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, date_joined, last_login FROM auth_user'
            )
            old_users = [dict(row) for row in cur.fetchall()]
        except sqlite3.OperationalError as e:
            self.stdout.write(self.style.ERROR(f'Tabela auth_user w starej bazie: {e}'))
            conn.close()
            return

        try:
            cur = conn.execute(
                'SELECT id, user_id, card_id, numer_kj, data_rejestracji, aktywna FROM qrp_app_rfidcard'
            )
            old_cards = [dict(row) for row in cur.fetchall()]
        except sqlite3.OperationalError as e:
            self.stdout.write(self.style.WARNING(f'Tabela qrp_app_rfidcard w starej bazie: {e} (pomijam karty)'))
            old_cards = []
        finally:
            conn.close()

        if dry_run:
            self.stdout.write(self.style.WARNING('TRYB DRY-RUN – brak zapisu'))
            self.stdout.write(f'Znaleziono w starej bazie: {len(old_users)} użytkowników, {len(old_cards)} kart RFID.')
            return

        # Mapowanie starych id użytkowników na nowych (w aktualnej bazie)
        old_id_to_user = {}
        created_users = 0
        updated_users = 0

        for row in old_users:
            username = (row['username'] or '').strip()
            if not username:
                continue
            date_joined = _parse_sqlite_datetime(row.get('date_joined')) or timezone.now()
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': row['first_name'] or '',
                    'last_name': row['last_name'] or '',
                    'email': row['email'] or '',
                    'password': row['password'] or '',
                    'is_staff': bool(row['is_staff']),
                    'is_active': bool(row['is_active']),
                    'is_superuser': bool(row['is_superuser']),
                    'date_joined': date_joined,
                }
            )
            if created:
                created_users += 1
            else:
                # Aktualizacja pól (hasło, imię, nazwisko, aktywność itd.)
                user.first_name = row['first_name'] or ''
                user.last_name = row['last_name'] or ''
                user.email = row['email'] or ''
                user.is_staff = bool(row['is_staff'])
                user.is_active = bool(row['is_active'])
                user.is_superuser = bool(row['is_superuser'])
                if row.get('password'):
                    user.password = row['password']
                user.save()
                updated_users += 1
            old_id_to_user[row['id']] = user

        created_cards = 0
        updated_cards = 0
        skipped_cards = 0

        for row in old_cards:
            new_user = old_id_to_user.get(row['user_id'])
            if not new_user:
                skipped_cards += 1
                continue
            card_id = (row['card_id'] or '').strip()
            if not card_id:
                continue
            card, created = RFIDCard.objects.get_or_create(
                card_id=card_id,
                defaults={
                    'user': new_user,
                    'numer_kj': (row['numer_kj'] or '').strip() or None,
                    'aktywna': bool(row['aktywna']) if row.get('aktywna') is not None else True,
                }
            )
            if created:
                created_cards += 1
            else:
                if card.user_id != new_user.id:
                    card.user = new_user
                    card.numer_kj = (row['numer_kj'] or '').strip() or None
                    card.aktywna = bool(row['aktywna']) if row.get('aktywna') is not None else True
                    card.save()
                    updated_cards += 1

        self.stdout.write(self.style.SUCCESS(
            f'Użytkownicy: {created_users} utworzonych, {updated_users} zaktualizowanych.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Karty RFID: {created_cards} utworzonych, {updated_cards} zaktualizowanych.'
        ))
        if skipped_cards:
            self.stdout.write(self.style.WARNING(f'Pominięto {skipped_cards} kart (brak użytkownika w starej bazie).'))
