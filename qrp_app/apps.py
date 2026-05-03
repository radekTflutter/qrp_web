from django.apps import AppConfig
from django.core.exceptions import AppRegistryNotReady


class QrpAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'qrp_app'
    verbose_name = 'QRP Control System'
    
    def ready(self):
        """
        Ładuje dozwolone adresy IP z bazy danych i dodaje do ALLOWED_HOSTS.
        Uruchamia scheduler synchronizacji poczekalni (gdy działa serwer WWW).
        """
        try:
            from django.conf import settings
            from .models import AllowedIP
            
            # Pobierz wszystkie aktywne adresy IP z bazy danych
            try:
                allowed_ips = AllowedIP.objects.filter(aktywny=True).values_list('ip_address', flat=True)
                
                # Dodaj IP do ALLOWED_HOSTS jeśli jeszcze nie ma
                for ip in allowed_ips:
                    ip_str = str(ip)
                    if ip_str not in settings.ALLOWED_HOSTS:
                        settings.ALLOWED_HOSTS.append(ip_str)
            except Exception:
                # Baza danych może nie być jeszcze gotowa (np. podczas migracji)
                # W takim przypadku po prostu pomiń
                pass
        except AppRegistryNotReady:
            # Aplikacja nie jest jeszcze gotowa
            pass

        # Scheduler poczekalni: co N minut wysyła rekordy na API (wątek daemon – nie blokuje migrate/shell)
        try:
            from .sync_scheduler import start_sync_scheduler
            start_sync_scheduler()
        except Exception:
            pass

