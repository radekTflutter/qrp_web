"""
Management command do automatycznej synchronizacji rekordów z centralnym API
oraz czyszczenia starych logów i danych.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from qrp_app.models import SystemSettings, SyncLog, Pomiar, Wada
from qrp_app.sync_service import send_to_central_api
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Synchronizuje zaległe rekordy z centralnym API i czyści stare logi/dane'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Symulacja bez rzeczywistych zmian (nie wysyła danych, nie usuwa)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('TRYB DRY-RUN - nie wprowadzam zmian'))

        try:
            settings_obj = SystemSettings.load()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Błąd podczas pobierania ustawień: {e}')
            )
            logger.error(f"Błąd pobierania ustawień systemowych: {e}")
            return

        # 1. Synchronizuj zaległe rekordy
        self.stdout.write('=' * 60)
        self.stdout.write('SYNCHRONIZACJA ZALEGŁYCH REKORDÓW')
        self.stdout.write('=' * 60)
        self._sync_pending_records(settings_obj, dry_run)

        # 2. Usuń stare logi
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('CZYSZCZENIE STARYCH LOGÓW')
        self.stdout.write('=' * 60)
        self._cleanup_old_logs(settings_obj, dry_run)

        # 3. Usuń stare zsynchronizowane rekordy
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('CZYSZCZENIE STARYCH REKORDÓW')
        self.stdout.write('=' * 60)
        self._cleanup_old_records(settings_obj, dry_run)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Wykonano wszystkie operacje'))

    def _sync_pending_records(self, settings_obj, dry_run):
        """Synchronizuje zaległe rekordy (is_synced=False)"""
        if not settings_obj.api_url or not settings_obj.api_token:
            self.stdout.write(
                self.style.WARNING('API centralne nie jest skonfigurowane - pomijam synchronizację')
            )
            return

        # Pobierz zaległe pomiary
        pending_measurements = Pomiar.objects.filter(is_synced=False)
        pending_defects = Wada.objects.filter(is_synced=False)

        total_pending = pending_measurements.count() + pending_defects.count()
        batch_size = settings_obj.retry_batch_size

        if total_pending == 0:
            self.stdout.write(self.style.SUCCESS('Brak zaległych rekordów do synchronizacji'))
            return

        self.stdout.write(f'Znaleziono {total_pending} zaległych rekordów')
        self.stdout.write(f'Rozmiar paczki: {batch_size}')

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY-RUN: Pominięto synchronizację {total_pending} rekordów'
                )
            )
            return

        # Wysyłaj w paczkach
        sent_count = 0
        failed_count = 0

        # Pomiary
        for measurement in pending_measurements[:batch_size]:
            if send_to_central_api(measurement):
                sent_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Pomiar #{measurement.id} - wysłano')
                )
            else:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Pomiar #{measurement.id} - błąd')
                )

        # Wady
        for defect in pending_defects[:batch_size]:
            if send_to_central_api(defect):
                sent_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Wada #{defect.id} - wysłano')
                )
            else:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Wada #{defect.id} - błąd')
                )

        self.stdout.write('')
        self.stdout.write(f'Synchronizacja zakończona: {sent_count} sukces, {failed_count} błędy')

    def _cleanup_old_logs(self, settings_obj, dry_run):
        """Usuwa stare logi synchronizacji"""
        if settings_obj.log_retention_days <= 0:
            self.stdout.write(
                self.style.WARNING('Retencja logów wyłączona (0 dni) - pomijam czyszczenie')
            )
            return

        cutoff_date = timezone.now() - timedelta(days=settings_obj.log_retention_days)
        old_logs = SyncLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('Brak starych logów do usunięcia'))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY-RUN: Usunięto by {count} logów starszych niż '
                    f'{settings_obj.log_retention_days} dni'
                )
            )
            return

        old_logs.delete()
        self.stdout.write(
            self.style.SUCCESS(f'Usunięto {count} starych logów (starszych niż {settings_obj.log_retention_days} dni)')
        )

    def _cleanup_old_records(self, settings_obj, dry_run):
        """Usuwa stare zsynchronizowane rekordy"""
        if settings_obj.data_retention_days <= 0:
            self.stdout.write(
                self.style.WARNING('Retencja danych wyłączona (0 dni) - pomijam czyszczenie')
            )
            return

        cutoff_date = timezone.now() - timedelta(days=settings_obj.data_retention_days)
        
        # Usuń tylko zsynchronizowane rekordy starsze niż cutoff_date
        old_measurements = Pomiar.objects.filter(
            is_synced=True,
            synced_at__lt=cutoff_date
        )
        old_defects = Wada.objects.filter(
            is_synced=True,
            synced_at__lt=cutoff_date
        )

        measurements_count = old_measurements.count()
        defects_count = old_defects.count()
        total_count = measurements_count + defects_count

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('Brak starych rekordów do usunięcia'))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY-RUN: Usunięto by {measurements_count} pomiarów i '
                    f'{defects_count} wad starszych niż {settings_obj.data_retention_days} dni'
                )
            )
            return

        old_measurements.delete()
        old_defects.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Usunięto {measurements_count} pomiarów i {defects_count} wad '
                f'(starszych niż {settings_obj.data_retention_days} dni)'
            )
        )
