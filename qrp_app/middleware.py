"""
Middleware do routingu na podstawie hostname DNS.
Pozwala na dostęp do aplikacji przez qrp-{identyfikator}.canpack.ad
"""
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import SuspiciousOperation
from .models import LiniaProdukcyjna, AllowedIP


class HostnameRoutingMiddleware(MiddlewareMixin):
    """
    Middleware, które wykrywa identyfikator linii z hostname
    i przypisuje go do requestu.
    
    Przykład:
    - qrp-l9.canpack.ad -> identyfikator: l9
    - qrp-l2.canpack.ad -> identyfikator: l2
    """
    
    def process_request(self, request):
        """
        Ekstraktuje identyfikator linii z hostname i przypisuje do requestu.
        """
        hostname = request.get_host().split(':')[0]  # Usuń port jeśli jest
        
        # Sprawdź czy to format qrp-{identyfikator}.canpack.ad
        if hostname.startswith('qrp-') and hostname.endswith('.canpack.ad'):
            # Wyciągnij identyfikator (np. l9 z qrp-l9.canpack.ad)
            parts = hostname.replace('.canpack.ad', '').split('-')
            if len(parts) >= 2:
                identyfikator = '-'.join(parts[1:])  # Dla przypadków jak qrp-l9-test
                identyfikator = identyfikator.lower().strip()
                
                # Spróbuj znaleźć linie produkcyjne z tym identyfikatorem (może być wiele)
                try:
                    linie = LiniaProdukcyjna.objects.filter(
                        identyfikator_dns=identyfikator,
                        aktywna=True
                    ).select_related('rejestrator').order_by('nazwa')
                    
                    if linie.exists():
                        # Przypisz wszystkie linie do requestu
                        request.active_lines = list(linie)  # Lista wszystkich linii
                        request.active_line = linie.first()  # Pierwsza linia (dla kompatybilności wstecznej)
                        request.line_identifier = identyfikator
                    else:
                        request.active_lines = []
                        request.active_line = None
                        request.line_identifier = identyfikator
                except Exception:
                    request.active_lines = []
                    request.active_line = None
                    request.line_identifier = None
            else:
                request.active_line = None
                request.line_identifier = None
        else:
            # Jeśli nie jest to format DNS, nie ustawiaj nic
            request.active_line = None
            request.line_identifier = None
        
        return None


class AllowedIPMiddleware(MiddlewareMixin):
    """
    Middleware, które dynamicznie dodaje nowe IP z bazy danych do ALLOWED_HOSTS.
    Sprawdza czy IP klienta jest na liście dozwolonych i jeśli tak, dodaje do ALLOWED_HOSTS.
    Musi być umieszczone PRZED SecurityMiddleware w settings.py.
    """
    
    def process_request(self, request):
        """
        Sprawdza czy IP klienta jest na liście dozwolonych adresów IP.
        Jeśli tak i nie ma w ALLOWED_HOSTS, dodaje go dynamicznie.
        """
        # Pobierz IP klienta
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # W przypadku proxy, pierwszy IP to IP klienta
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        # Sprawdź czy IP jest na liście dozwolonych
        try:
            allowed_ip = AllowedIP.objects.filter(
                ip_address=ip,
                aktywny=True
            ).first()
            
            if allowed_ip:
                # IP jest dozwolone - zapisz w requestie
                request.allowed_ip = allowed_ip
                
                # Dodaj IP do ALLOWED_HOSTS jeśli jeszcze nie ma
                # Uwaga: settings są immutable, ale możemy modyfikować listę
                from django.conf import settings
                
                # Konwertuj na listę jeśli to tuple
                if isinstance(settings.ALLOWED_HOSTS, tuple):
                    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS)
                
                # Dodaj IP jeśli jeszcze nie ma
                if ip not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(ip)
                
                # Dodaj hostname jeśli jeszcze nie ma
                hostname = request.get_host().split(':')[0]
                if hostname not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(hostname)
            else:
                request.allowed_ip = None
        except Exception:
            # W przypadku błędu (np. baza danych nie jest jeszcze gotowa), nie blokuj
            request.allowed_ip = None
        
        return None
