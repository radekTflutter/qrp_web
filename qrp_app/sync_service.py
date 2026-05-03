"""
Serwis synchronizacji danych z centralnym API.
Obsługuje wysyłanie pomiarów i wad do centralnego systemu.
"""
import logging
import socket
try:
    import requests
except ImportError:
    requests = None
from typing import Optional, Dict, Any
from django.core.files.base import File
from django.conf import settings
from django.utils import timezone
from .models import SystemSettings, SyncLog, Pomiar, Wada

logger = logging.getLogger(__name__)

# Timeout dla żądań HTTP (30 sekund)
REQUEST_TIMEOUT = 30
# Krótszy timeout dla weryfikacji GET (czy rekord jest już na serwerze)
VERIFY_TIMEOUT = 10


def _verify_record_on_server(instance: Pomiar | Wada, base_url: str, settings_obj) -> bool:
    """
    Sprawdza, czy rekord jest już zapisany na serwerze centralnym (GET).
    Dopasowanie po (record_id, registrar_id), żeby nie mylić rekordów z różnych rejestratorów.
    """
    if requests is None:
        return False
    record_id = instance.id
    our_registrar_id = _get_registrar_id(instance)
    if isinstance(instance, Pomiar):
        check_url = f"{base_url}/measurements/{record_id}/"
        list_key = "measurements"
    else:
        check_url = f"{base_url}/defects/{record_id}/"
        list_key = "defects"
    headers = {"Accept": "application/json"}
    if getattr(settings_obj, "api_token", None):
        headers["Authorization"] = f"Bearer {settings_obj.api_token}"
    try:
        r = requests.get(check_url, headers=headers, timeout=VERIFY_TIMEOUT)
        if r.status_code != 200:
            return False
        data = r.json()
        if not data.get("success"):
            return False
        items = data.get(list_key) or []
        for item in items:
            if item.get("record_id") != record_id:
                continue
            # Dopasuj po registrar_id, jeśli serwer go zwraca (unika podwójnych id z różnych rejestratorów)
            resp_registrar = item.get("registrar_id")
            if resp_registrar is not None and resp_registrar != our_registrar_id:
                continue
            return True
        return False
    except Exception:
        return False


def _get_registrar_id(instance: Pomiar | Wada) -> str:
    """
    Pobiera unikalny identyfikator rejestratora z nazwy rejestratora.
    Próbuje kolejno:
    1. Nazwa rejestratora z instancji (instance.linia_produkcyjna.rejestrator.nazwa) - NAJLEPSZE
    2. SystemSettings.registrar_id (jeśli pole istnieje)
    3. Hostname komputera
    4. IP adres komputera
    
    Args:
        instance: Instancja modelu Pomiar lub Wada
    
    Returns:
        str: Identyfikator rejestratora
    """
    try:
        # Próba 1: Nazwa rejestratora z instancji (NAJLEPSZE - z panelu admin)
        if instance.linia_produkcyjna and instance.linia_produkcyjna.rejestrator:
            registrar_name = instance.linia_produkcyjna.rejestrator.nazwa
            if registrar_name:
                return registrar_name
    except Exception:
        pass
    
    try:
        # Próba 2: Z SystemSettings (jeśli pole istnieje)
        settings_obj = SystemSettings.load()
        if hasattr(settings_obj, 'registrar_id') and settings_obj.registrar_id:
            return settings_obj.registrar_id
    except Exception:
        pass
    
    try:
        # Próba 3: Hostname komputera
        hostname = socket.gethostname()
        if hostname:
            return hostname
    except Exception:
        pass
    
    try:
        # Próba 4: IP adres komputera
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        if ip_address:
            return ip_address
    except Exception:
        pass
    
    # Fallback: domyślna wartość
    return "UNKNOWN"


def _mark_synced(instance: Pomiar | Wada) -> None:
    """Oznacza rekord jako zsynchronizowany w bazie (bez logowania)."""
    model_class = type(instance)
    model_class.objects.filter(pk=instance.pk).update(
        is_synced=True,
        synced_at=timezone.now()
    )


def send_to_central_api(instance: Pomiar | Wada) -> bool:
    """
    Wysyła pojedynczy rekord (Pomiar lub Wada) do centralnego API.
    
    Args:
        instance: Instancja modelu Pomiar lub Wada do wysłania
        
    Returns:
        bool: True jeśli synchronizacja się powiodła, False w przeciwnym razie
    """
    # Pobierz ustawienia systemowe
    try:
        settings_obj = SystemSettings.load()
    except Exception as e:
        logger.error(f"Błąd podczas pobierania ustawień systemowych: {e}")
        _log_sync_error(None, f"Błąd pobierania ustawień: {str(e)}", instance)
        return False
    
    # Sprawdź czy API jest skonfigurowane
    if not settings_obj.api_url:
        logger.warning("API centralne nie jest skonfigurowane (brak URL)")
        _log_sync_error(None, "API centralne nie jest skonfigurowane (brak URL)", instance)
        return False
    
    # Określ endpoint w zależności od typu rekordu
    # api_url powinien być bazowym URL (np. http://10.11.1.1:8000/api)
    # Dodajemy odpowiednią ścieżkę: /measurements/ lub /defects/
    base_url = settings_obj.api_url.rstrip('/')
    if isinstance(instance, Pomiar):
        api_endpoint = f"{base_url}/measurements/"
    else:  # Wada
        api_endpoint = f"{base_url}/defects/"
    
    # Przygotuj dane do wysyłki
    try:
        data = _prepare_data(instance)
        files = _prepare_files(instance)
    except Exception as e:
        logger.error(f"Błąd podczas przygotowywania danych: {e}")
        _log_sync_error(None, f"Błąd przygotowania danych: {str(e)}", instance)
        return False
    
    # Wykonaj żądanie HTTP
    if requests is None:
        logger.error("Module 'requests' is not installed. Cannot send data to central API.")
        _log_sync_error(None, "Moduł 'requests' nie jest zainstalowany", instance)
        return False
    
    try:
        headers = {
            'Accept': 'application/json',
        }
        # Dodaj token autoryzacji tylko jeśli jest ustawiony
        if settings_obj.api_token:
            headers['Authorization'] = f'Bearer {settings_obj.api_token}'
        
        # Jeśli są pliki, wysyłamy jako multipart/form-data
        # W przeciwnym razie jako JSON
        if files:
            # Multipart/form-data - dane JSON jako string w polu 'data'
            import json as json_module
            form_data = {
                'data': json_module.dumps(data, ensure_ascii=False)
            }
            response = requests.post(
                api_endpoint,
                data=form_data,
                files=files,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
        else:
            # Tylko JSON
            response = requests.post(
                api_endpoint,
                json=data,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
        
        # Sprawdź odpowiedź – każdy status 2xx uznajemy za sukces
        if 200 <= response.status_code < 300:
            _mark_synced(instance)
            _log_sync_success(response.status_code, f"Rekord #{instance.id} zsynchronizowany pomyślnie", instance)
            logger.info(f"Sukces synchronizacji rekordu {type(instance).__name__} #{instance.id}")
            return True
        else:
            # Błąd HTTP
            error_msg = f"Błąd HTTP {response.status_code}: {response.text[:200]}"
            _log_sync_error(response.status_code, error_msg, instance)
            logger.error(
                "Błąd synchronizacji rekordu %s #%s (endpoint %s): %s",
                type(instance).__name__, instance.id, api_endpoint, error_msg
            )
            return False
            
    except requests.exceptions.Timeout:
        error_msg = "Timeout podczas połączenia z API centralnym"
        if _verify_record_on_server(instance, base_url, settings_obj):
            _mark_synced(instance)
            _log_sync_success(0, f"Rekord #{instance.id} już na serwerze (weryfikacja GET po timeout)", instance)
            logger.info("Rekord %s #%s już na serwerze (weryfikacja GET po timeout) – oznaczono jako zsynchronizowany", type(instance).__name__, instance.id)
            return True
        _log_sync_error(None, error_msg, instance)
        logger.error(f"Timeout podczas synchronizacji rekordu {type(instance).__name__} #{instance.id}")
        return False
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Błąd połączenia z API centralnym: {str(e)}"
        if _verify_record_on_server(instance, base_url, settings_obj):
            _mark_synced(instance)
            _log_sync_success(0, f"Rekord #{instance.id} już na serwerze (weryfikacja GET po błędzie połączenia)", instance)
            logger.info("Rekord %s #%s już na serwerze (weryfikacja GET po błędzie połączenia) – oznaczono jako zsynchronizowany", type(instance).__name__, instance.id)
            return True
        _log_sync_error(None, error_msg, instance)
        logger.error(f"Błąd połączenia podczas synchronizacji rekordu {type(instance).__name__} #{instance.id}")
        return False
    except Exception as e:
        # Ogólny błąd - aplikacja nie może się wywalić
        error_msg = f"Nieoczekiwany błąd podczas synchronizacji: {str(e)}"
        _log_sync_error(None, error_msg, instance)
        logger.exception(f"Nieoczekiwany błąd podczas synchronizacji rekordu {type(instance).__name__} #{instance.id}")
        return False
    finally:
        # Upewnij się, że pliki są zamknięte (zapobieganie wyciekom pamięci)
        if files:
            for file_obj in files.values():
                if hasattr(file_obj, 'close'):
                    try:
                        file_obj.close()
                    except Exception:
                        pass


def _prepare_data(instance: Pomiar | Wada) -> Dict[str, Any]:
    """
    Przygotowuje dane do wysłania do API.
    
    Args:
        instance: Instancja modelu Pomiar lub Wada
        
    Returns:
        dict: Słownik z danymi do wysłania
    """
    # Przy USE_TZ=False data_utworzenia jest naiwna (już w czasie lokalnym).
    # Przy USE_TZ=True konwertuj UTC → lokalny.
    dt = instance.data_utworzenia
    if dt is not None and getattr(dt, 'tzinfo', None) and dt.tzinfo:
        dt = timezone.localtime(dt)
    local_datetime = dt
    
    base_data = {
        'record_id': instance.id,
        'registrar_id': _get_registrar_id(instance),  # Dodaj identyfikator rejestratora (nazwa z panelu admin)
        'record_type': 'measurement' if isinstance(instance, Pomiar) else 'defect',
        'line_name': str(instance.linia_produkcyjna),
        'line_id': instance.linia_produkcyjna.id,
        'user': instance.uzytkownik.username if instance.uzytkownik else None,
        'order_number': instance.numer_zlecenia,
        'control_type': str(instance.typ_kontroli),  # Konwertuj na string
        'created_at': local_datetime.isoformat() if local_datetime else timezone.now().isoformat(),
    }
    
    if isinstance(instance, Pomiar):
        base_data.update({
            'test_type': str(instance.rodzaj_testu),  # Konwertuj na string (kod)
            'test_type_display': instance.get_rodzaj_testu_display(),  # Pełna nazwa
            'comment': instance.komentarz,
        })
    elif isinstance(instance, Wada):
        base_data.update({
            'defect_description': (instance.opis_wady or '').strip() or ' ',
            'comment': instance.komentarz or '',
        })
    
    return base_data


def _prepare_files(instance: Pomiar | Wada) -> Dict[str, File]:
    """
    Przygotowuje pliki (zdjęcia) do wysłania do API.
    Dla wad zdjęcie może być w podkatalogu 'wady/' – obsługa jak dla pomiarów.
    """
    files = {}
    
    if not getattr(instance, 'zdjecie', None):
        return files
    zdjecie = instance.zdjecie
    name = getattr(zdjecie, 'name', None) if zdjecie else None
    if not name:
        return files
    try:
        photo_file = zdjecie.open('rb')
        files['photo'] = (
            name.split('/')[-1] if '/' in name else name,
            photo_file,
            'image/jpeg'
        )
    except Exception as e:
        logger.warning("Nie udało się otworzyć zdjęcia dla rekordu %s #%s: %s", type(instance).__name__, instance.pk, e)
    
    return files


def _log_sync_success(status_code: int, message: str, instance: Pomiar | Wada):
    """Loguje sukces synchronizacji"""
    SyncLog.objects.create(
        status_code=status_code,
        message=message,
        is_success=True,
        record_type='measurement' if isinstance(instance, Pomiar) else 'defect',
        record_id=instance.id
    )


def _log_sync_error(status_code: Optional[int], message: str, instance: Pomiar | Wada):
    """Loguje błąd synchronizacji"""
    SyncLog.objects.create(
        status_code=status_code,
        message=message,
        is_success=False,
        record_type='measurement' if isinstance(instance, Pomiar) else 'defect',
        record_id=instance.id
    )
