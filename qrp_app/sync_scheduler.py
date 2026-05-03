"""
Scheduler synchronizacji poczekalni z centralnym API.
Uruchamia w tle wątek, który co N minut (retry_interval_minutes) wysyła
niezsynchronizowane pomiary i wady do API – niezależnie od tego, czy
użytkownik ma otwartą stronę archiwum.
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

_scheduler_started = False
_scheduler_lock = threading.Lock()


def _sync_pending_loop():
    """Pętla w tle: co retry_interval_minutes wysyła rekordy z poczekalni."""
    from django.db import close_old_connections
    from .models import SystemSettings, Pomiar, Wada
    from .sync_service import send_to_central_api

    # Poczekaj na start serwera i gotowość bazy
    time.sleep(60)

    while True:
        try:
            close_old_connections()
            settings_obj = SystemSettings.load()
            if not settings_obj.api_url:
                time.sleep(300)
                continue

            interval_minutes = getattr(settings_obj, 'retry_interval_minutes', 15)
            batch_size = getattr(settings_obj, 'retry_batch_size', 10)

            pending_measurements = list(
                Pomiar.objects.filter(is_synced=False)[:batch_size]
            )
            pending_defects = list(
                Wada.objects.filter(is_synced=False)[:batch_size]
            )

            synced = 0
            for m in pending_measurements:
                try:
                    if send_to_central_api(m):
                        synced += 1
                except Exception as e:
                    logger.exception("Błąd synchronizacji pomiaru #%s: %s", m.id, e)
            for w in pending_defects:
                try:
                    if send_to_central_api(w):
                        synced += 1
                except Exception as e:
                    logger.exception("Błąd synchronizacji wady #%s: %s", w.id, e)

            if synced:
                logger.info("Scheduler: zsynchronizowano %s rekordów z poczekalni.", synced)
        except Exception as e:
            logger.exception("Błąd w pętli synchronizacji poczekalni: %s", e)
        finally:
            close_old_connections()

        try:
            settings_obj = SystemSettings.load()
            interval_minutes = getattr(settings_obj, 'retry_interval_minutes', 15)
        except Exception:
            interval_minutes = 15
        time.sleep(max(1, interval_minutes) * 60)


def start_sync_scheduler():
    """Uruchamia wątek wysyłający rekordy z poczekalni co N minut."""
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True
    t = threading.Thread(target=_sync_pending_loop, daemon=True, name="qrpsync")
    t.start()
    logger.info("Scheduler synchronizacji poczekalni uruchomiony (wątek w tle).")
