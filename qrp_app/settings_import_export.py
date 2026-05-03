"""
Funkcje do importu i eksportu ustawień systemowych z panelu admina.
"""
import json
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import (
    SystemSettings, Rejestrator, LiniaProdukcyjna, AllowedIP,
    TypKontroli, RodzajTestu, ZmiennaPLC
)


def export_settings_to_json():
    """
    Eksportuje wszystkie ustawienia systemowe do formatu JSON.
    Zwraca słownik z danymi wszystkich modeli konfiguracyjnych.
    """
    data = {
        'version': '1.0',
        'export_date': None,
        'system_settings': None,
        'rejestratory': [],
        'linie_produkcyjne': [],
        'allowed_ips': [],
        'typy_kontroli': [],
        'rodzaje_testu': [],
        'zmienne_plc': [],
    }
    
    # SystemSettings (singleton)
    try:
        settings = SystemSettings.load()
        data['system_settings'] = {
            'api_url': settings.api_url,
            'api_token': settings.api_token,
            'log_retention_days': settings.log_retention_days,
            'data_retention_days': settings.data_retention_days,
            'retry_interval_minutes': settings.retry_interval_minutes,
            'retry_batch_size': settings.retry_batch_size,
            'show_sync_status': settings.show_sync_status,
            'show_sync_column': settings.show_sync_column,
            'csv_export_enabled': settings.csv_export_enabled,
            'csv_output_path': settings.csv_output_path,
            'csv_line_mapping': settings.csv_line_mapping,
            'csv_machine_mapping': settings.csv_machine_mapping,
            'csv_inspection_mapping': settings.csv_inspection_mapping,
            'auto_logout_enabled': settings.auto_logout_enabled,
            'auto_logout_timeout_minutes': settings.auto_logout_timeout_minutes,
        }
    except Exception as e:
        data['system_settings'] = {'error': str(e)}
    
    # Rejestratory
    for rej in Rejestrator.objects.all():
        rej_data = {
            'nazwa': rej.nazwa,
            'url_kamery': rej.url_kamery,
            'opis': rej.opis,
            'aktywny': rej.aktywny,
            'domyslny_typ_kontroli': rej.domyslny_typ_kontroli.nazwa if rej.domyslny_typ_kontroli else None,
            'domyslny_rodzaj_testu': rej.domyslny_rodzaj_testu.nazwa if rej.domyslny_rodzaj_testu else None,
            'dla_kj': rej.dla_kj,
            'dostepne_typy_kontroli': [tk.nazwa for tk in rej.dostepne_typy_kontroli.all()],
            'dostepne_rodzaje_testu': [rt.nazwa for rt in rej.dostepne_rodzaje_testu.all()],
        }
        data['rejestratory'].append(rej_data)
    
    # Linie produkcyjne
    for linia in LiniaProdukcyjna.objects.all():
        linia_data = {
            'rejestrator_nazwa': linia.rejestrator.nazwa,
            'nazwa': linia.nazwa,
            'url_kamery': linia.url_kamery,
            'ip_plc': str(linia.ip_plc),
            'zmienna_numer_zlecenia': linia.zmienna_numer_zlecenia,
            'identyfikator_dns': linia.identyfikator_dns,
            'aktywna': linia.aktywna,
            'opis': linia.opis,
        }
        data['linie_produkcyjne'].append(linia_data)
    
    # AllowedIP
    for ip in AllowedIP.objects.all():
        ip_data = {
            'ip_address': str(ip.ip_address),
            'opis': ip.opis,
            'aktywny': ip.aktywny,
        }
        data['allowed_ips'].append(ip_data)
    
    # Typy kontroli
    for typ in TypKontroli.objects.all():
        typ_data = {
            'nazwa': typ.nazwa,
            'kod': typ.kod,
            'aktywny': typ.aktywny,
            'kolejnosc': typ.kolejnosc,
        }
        data['typy_kontroli'].append(typ_data)
    
    # Rodzaje testu
    for rodzaj in RodzajTestu.objects.all():
        rodzaj_data = {
            'nazwa': rodzaj.nazwa,
            'kod': rodzaj.kod,
            'aktywny': rodzaj.aktywny,
            'kolejnosc': rodzaj.kolejnosc,
        }
        data['rodzaje_testu'].append(rodzaj_data)
    
    # Zmienne PLC
    for zmienna in ZmiennaPLC.objects.all():
        zmienna_data = {
            'nazwa': zmienna.nazwa,
            'typ_danych': zmienna.typ_danych,
            'wartosc_domyslna': zmienna.wartosc_domyslna,
            'opis': zmienna.opis,
        }
        data['zmienne_plc'].append(zmienna_data)
    
    return data


def import_settings_from_json(json_data, dry_run=False, overwrite_mode=False):
    """
    Importuje ustawienia z formatu JSON.
    
    Args:
        json_data: Słownik z danymi do zaimportowania
        dry_run: Jeśli True, tylko waliduje dane bez zapisywania
        overwrite_mode: Jeśli True, usuwa wszystkie istniejące dane (oprócz SystemSettings) przed importem
    
    Returns:
        Słownik z wynikami importu: {'success': bool, 'created': int, 'updated': int, 'deleted': int, 'errors': list}
    """
    results = {
        'success': True,
        'created': 0,
        'updated': 0,
        'deleted': 0,
        'errors': [],
        'warnings': [],
    }
    
    try:
        with transaction.atomic():
            # Tryb nadpisywania - usuń wszystkie istniejące dane (oprócz SystemSettings)
            if overwrite_mode and not dry_run:
                deleted_count = 0
                # Usuń w odpowiedniej kolejności (najpierw zależne, potem niezależne)
                deleted_count += LiniaProdukcyjna.objects.all().delete()[0]
                deleted_count += Rejestrator.objects.all().delete()[0]
                deleted_count += AllowedIP.objects.all().delete()[0]
                deleted_count += TypKontroli.objects.all().delete()[0]
                deleted_count += RodzajTestu.objects.all().delete()[0]
                deleted_count += ZmiennaPLC.objects.all().delete()[0]
                results['deleted'] = deleted_count
                results['warnings'].append(f"Usunięto {deleted_count} istniejących rekordów przed importem (tryb nadpisywania)")
            elif overwrite_mode and dry_run:
                # W trybie testowym tylko policz ile by zostało usunięte
                count = (
                    LiniaProdukcyjna.objects.count() +
                    Rejestrator.objects.count() +
                    AllowedIP.objects.count() +
                    TypKontroli.objects.count() +
                    RodzajTestu.objects.count() +
                    ZmiennaPLC.objects.count()
                )
                results['deleted'] = count
                results['warnings'].append(f"W trybie nadpisywania zostałoby usuniętych {count} istniejących rekordów")
            # SystemSettings
            if 'system_settings' in json_data and json_data['system_settings']:
                try:
                    settings = SystemSettings.load()
                    settings_data = json_data['system_settings']
                    
                    if 'error' not in settings_data:
                        settings.api_url = settings_data.get('api_url', settings.api_url)
                        settings.api_token = settings_data.get('api_token', settings.api_token)
                        settings.log_retention_days = settings_data.get('log_retention_days', settings.log_retention_days)
                        settings.data_retention_days = settings_data.get('data_retention_days', settings.data_retention_days)
                        settings.retry_interval_minutes = settings_data.get('retry_interval_minutes', settings.retry_interval_minutes)
                        settings.retry_batch_size = settings_data.get('retry_batch_size', settings.retry_batch_size)
                        settings.show_sync_status = settings_data.get('show_sync_status', settings.show_sync_status)
                        settings.show_sync_column = settings_data.get('show_sync_column', settings.show_sync_column)
                        settings.csv_export_enabled = settings_data.get('csv_export_enabled', settings.csv_export_enabled)
                        settings.csv_output_path = settings_data.get('csv_output_path', settings.csv_output_path)
                        settings.csv_line_mapping = settings_data.get('csv_line_mapping', settings.csv_line_mapping)
                        settings.csv_machine_mapping = settings_data.get('csv_machine_mapping', settings.csv_machine_mapping)
                        settings.csv_inspection_mapping = settings_data.get('csv_inspection_mapping', settings.csv_inspection_mapping)
                        settings.auto_logout_enabled = settings_data.get('auto_logout_enabled', settings.auto_logout_enabled)
                        settings.auto_logout_timeout_minutes = settings_data.get('auto_logout_timeout_minutes', settings.auto_logout_timeout_minutes)
                        
                        if not dry_run:
                            settings.save()
                            results['updated'] += 1
                except Exception as e:
                    results['errors'].append(f"Błąd importu SystemSettings: {str(e)}")
                    results['success'] = False
            
            # Typy kontroli (najpierw, bo są używane przez rejestratory)
            if 'typy_kontroli' in json_data:
                for typ_data in json_data['typy_kontroli']:
                    try:
                        typ, created = TypKontroli.objects.get_or_create(
                            kod=typ_data.get('kod'),
                            defaults={
                                'nazwa': typ_data.get('nazwa', ''),
                                'aktywny': typ_data.get('aktywny', True),
                                'kolejnosc': typ_data.get('kolejnosc', 0),
                            }
                        )
                        if not created:
                            typ.nazwa = typ_data.get('nazwa', typ.nazwa)
                            typ.aktywny = typ_data.get('aktywny', typ.aktywny)
                            typ.kolejnosc = typ_data.get('kolejnosc', typ.kolejnosc)
                            if not dry_run:
                                typ.save()
                            results['updated'] += 1
                        else:
                            if not dry_run:
                                typ.save()
                            results['created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Błąd importu TypKontroli '{typ_data.get('nazwa', '?')}': {str(e)}")
            
            # Rodzaje testu (najpierw, bo są używane przez rejestratory)
            if 'rodzaje_testu' in json_data:
                for rodzaj_data in json_data['rodzaje_testu']:
                    try:
                        if overwrite_mode:
                            # W trybie nadpisywania zawsze tworzymy nowy (stare już zostały usunięte)
                            rodzaj = RodzajTestu(
                                kod=rodzaj_data.get('kod'),
                                nazwa=rodzaj_data.get('nazwa', ''),
                                aktywny=rodzaj_data.get('aktywny', True),
                                kolejnosc=rodzaj_data.get('kolejnosc', 0),
                            )
                            if not dry_run:
                                rodzaj.save()
                            results['created'] += 1
                        else:
                            # Tryb dopisywania - aktualizuj lub utwórz
                            rodzaj, created = RodzajTestu.objects.get_or_create(
                                kod=rodzaj_data.get('kod'),
                                defaults={
                                    'nazwa': rodzaj_data.get('nazwa', ''),
                                    'aktywny': rodzaj_data.get('aktywny', True),
                                    'kolejnosc': rodzaj_data.get('kolejnosc', 0),
                                }
                            )
                            if not created:
                                rodzaj.nazwa = rodzaj_data.get('nazwa', rodzaj.nazwa)
                                rodzaj.aktywny = rodzaj_data.get('aktywny', rodzaj.aktywny)
                                rodzaj.kolejnosc = rodzaj_data.get('kolejnosc', rodzaj.kolejnosc)
                                if not dry_run:
                                    rodzaj.save()
                                results['updated'] += 1
                            else:
                                if not dry_run:
                                    rodzaj.save()
                                results['created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Błąd importu RodzajTestu '{rodzaj_data.get('nazwa', '?')}': {str(e)}")
            
            # Rejestratory
            if 'rejestratory' in json_data:
                for rej_data in json_data['rejestratory']:
                    try:
                        rej, created = Rejestrator.objects.get_or_create(
                            nazwa=rej_data.get('nazwa'),
                            defaults={
                                'url_kamery': rej_data.get('url_kamery', ''),
                                'opis': rej_data.get('opis', ''),
                                'aktywny': rej_data.get('aktywny', True),
                                'dla_kj': rej_data.get('dla_kj', True),
                            }
                        )
                        if not created:
                            rej.url_kamery = rej_data.get('url_kamery', rej.url_kamery)
                            rej.opis = rej_data.get('opis', rej.opis)
                            rej.aktywny = rej_data.get('aktywny', rej.aktywny)
                            rej.dla_kj = rej_data.get('dla_kj', rej.dla_kj)
                            if not dry_run:
                                rej.save()
                            results['updated'] += 1
                        else:
                            if not dry_run:
                                rej.save()
                            results['created'] += 1
                        
                        # Przypisz domyślne typy kontroli i rodzaje testu
                        if not dry_run:
                            if rej_data.get('domyslny_typ_kontroli'):
                                try:
                                    typ = TypKontroli.objects.get(nazwa=rej_data['domyslny_typ_kontroli'])
                                    rej.domyslny_typ_kontroli = typ
                                    rej.save()
                                except TypKontroli.DoesNotExist:
                                    results['warnings'].append(f"Typ kontroli '{rej_data['domyslny_typ_kontroli']}' nie istnieje dla rejestratora '{rej.nazwa}'")
                            
                            if rej_data.get('domyslny_rodzaj_testu'):
                                try:
                                    rodzaj = RodzajTestu.objects.get(nazwa=rej_data['domyslny_rodzaj_testu'])
                                    rej.domyslny_rodzaj_testu = rodzaj
                                    rej.save()
                                except RodzajTestu.DoesNotExist:
                                    results['warnings'].append(f"Rodzaj testu '{rej_data['domyslny_rodzaj_testu']}' nie istnieje dla rejestratora '{rej.nazwa}'")
                            
                            # Przypisz dostępne typy kontroli
                            rej.dostepne_typy_kontroli.clear()
                            for typ_nazwa in rej_data.get('dostepne_typy_kontroli', []):
                                try:
                                    typ = TypKontroli.objects.get(nazwa=typ_nazwa)
                                    rej.dostepne_typy_kontroli.add(typ)
                                except TypKontroli.DoesNotExist:
                                    results['warnings'].append(f"Typ kontroli '{typ_nazwa}' nie istnieje")
                            
                            # Przypisz dostępne rodzaje testu
                            rej.dostepne_rodzaje_testu.clear()
                            for rodzaj_nazwa in rej_data.get('dostepne_rodzaje_testu', []):
                                try:
                                    rodzaj = RodzajTestu.objects.get(nazwa=rodzaj_nazwa)
                                    rej.dostepne_rodzaje_testu.add(rodzaj)
                                except RodzajTestu.DoesNotExist:
                                    results['warnings'].append(f"Rodzaj testu '{rodzaj_nazwa}' nie istnieje")
                    except Exception as e:
                        results['errors'].append(f"Błąd importu Rejestrator '{rej_data.get('nazwa', '?')}': {str(e)}")
            
            # Linie produkcyjne
            if 'linie_produkcyjne' in json_data:
                for linia_data in json_data['linie_produkcyjne']:
                    try:
                        rejestrator_nazwa = linia_data.get('rejestrator_nazwa')
                        if not rejestrator_nazwa:
                            results['errors'].append(f"Brak nazwy rejestratora dla linii '{linia_data.get('nazwa', '?')}'")
                            continue
                        
                        try:
                            rejestrator = Rejestrator.objects.get(nazwa=rejestrator_nazwa)
                        except Rejestrator.DoesNotExist:
                            results['errors'].append(f"Rejestrator '{rejestrator_nazwa}' nie istnieje dla linii '{linia_data.get('nazwa', '?')}'")
                            continue
                        
                        linia, created = LiniaProdukcyjna.objects.get_or_create(
                            nazwa=linia_data.get('nazwa'),
                            rejestrator=rejestrator,
                            defaults={
                                'url_kamery': linia_data.get('url_kamery', ''),
                                'ip_plc': linia_data.get('ip_plc', ''),
                                'zmienna_numer_zlecenia': linia_data.get('zmienna_numer_zlecenia', ''),
                                'identyfikator_dns': linia_data.get('identyfikator_dns', ''),
                                'aktywna': linia_data.get('aktywna', True),
                                'opis': linia_data.get('opis', ''),
                            }
                        )
                        if not created:
                            linia.url_kamery = linia_data.get('url_kamery', linia.url_kamery)
                            linia.ip_plc = linia_data.get('ip_plc', linia.ip_plc)
                            linia.zmienna_numer_zlecenia = linia_data.get('zmienna_numer_zlecenia', linia.zmienna_numer_zlecenia)
                            linia.identyfikator_dns = linia_data.get('identyfikator_dns', linia.identyfikator_dns)
                            linia.aktywna = linia_data.get('aktywna', linia.aktywna)
                            linia.opis = linia_data.get('opis', linia.opis)
                            if not dry_run:
                                linia.save()
                            results['updated'] += 1
                        else:
                            if not dry_run:
                                linia.save()
                            results['created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Błąd importu LiniaProdukcyjna '{linia_data.get('nazwa', '?')}': {str(e)}")
            
            # AllowedIP
            if 'allowed_ips' in json_data:
                for ip_data in json_data['allowed_ips']:
                    try:
                        if overwrite_mode:
                            # W trybie nadpisywania zawsze tworzymy nowy (stare już zostały usunięte)
                            ip = AllowedIP(
                                ip_address=ip_data.get('ip_address'),
                                opis=ip_data.get('opis', ''),
                                aktywny=ip_data.get('aktywny', True),
                            )
                            if not dry_run:
                                ip.save()
                            results['created'] += 1
                        else:
                            # Tryb dopisywania - aktualizuj lub utwórz
                            ip, created = AllowedIP.objects.get_or_create(
                                ip_address=ip_data.get('ip_address'),
                                defaults={
                                    'opis': ip_data.get('opis', ''),
                                    'aktywny': ip_data.get('aktywny', True),
                                }
                            )
                            if not created:
                                ip.opis = ip_data.get('opis', ip.opis)
                                ip.aktywny = ip_data.get('aktywny', ip.aktywny)
                                if not dry_run:
                                    ip.save()
                                results['updated'] += 1
                            else:
                                if not dry_run:
                                    ip.save()
                                results['created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Błąd importu AllowedIP '{ip_data.get('ip_address', '?')}': {str(e)}")
            
            # Zmienne PLC
            if 'zmienne_plc' in json_data:
                for zmienna_data in json_data['zmienne_plc']:
                    try:
                        # Zmienne PLC są powiązane z liniami produkcyjnymi, więc potrzebujemy linii
                        # W trybie nadpisywania linie już zostały usunięte, więc zmienne też
                        # Ale musimy znaleźć odpowiednią linię dla zmiennej
                        linia_nazwa = zmienna_data.get('linia_produkcyjna_nazwa')  # Możemy dodać to do eksportu
                        if not linia_nazwa:
                            # Jeśli nie ma nazwy linii w danych, pomiń (zmienne PLC są inline w liniach)
                            results['warnings'].append(f"Zmienna PLC '{zmienna_data.get('nazwa', '?')}' nie ma przypisanej linii produkcyjnej - pominięta")
                            continue
                        
                        try:
                            linia = LiniaProdukcyjna.objects.get(nazwa=linia_nazwa)
                        except LiniaProdukcyjna.DoesNotExist:
                            results['warnings'].append(f"Linia produkcyjna '{linia_nazwa}' nie istnieje dla zmiennej PLC '{zmienna_data.get('nazwa', '?')}' - pominięta")
                            continue
                        
                        if overwrite_mode:
                            # W trybie nadpisywania zawsze tworzymy nowy (stare już zostały usunięte)
                            zmienna = ZmiennaPLC(
                                nazwa=zmienna_data.get('nazwa'),
                                linia_produkcyjna=linia,
                                typ_danych=zmienna_data.get('typ_danych', 'STRING'),
                                wartosc_domyslna=zmienna_data.get('wartosc_domyslna', ''),
                                opis=zmienna_data.get('opis', ''),
                            )
                            if not dry_run:
                                zmienna.save()
                            results['created'] += 1
                        else:
                            # Tryb dopisywania - aktualizuj lub utwórz
                            zmienna, created = ZmiennaPLC.objects.get_or_create(
                                nazwa=zmienna_data.get('nazwa'),
                                linia_produkcyjna=linia,
                                defaults={
                                    'typ_danych': zmienna_data.get('typ_danych', 'STRING'),
                                    'wartosc_domyslna': zmienna_data.get('wartosc_domyslna', ''),
                                    'opis': zmienna_data.get('opis', ''),
                                }
                            )
                            if not created:
                                zmienna.typ_danych = zmienna_data.get('typ_danych', zmienna.typ_danych)
                                zmienna.wartosc_domyslna = zmienna_data.get('wartosc_domyslna', zmienna.wartosc_domyslna)
                                zmienna.opis = zmienna_data.get('opis', zmienna.opis)
                                if not dry_run:
                                    zmienna.save()
                                results['updated'] += 1
                            else:
                                if not dry_run:
                                    zmienna.save()
                                results['created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Błąd importu ZmiennaPLC '{zmienna_data.get('nazwa', '?')}': {str(e)}")
            
            if dry_run:
                # W trybie dry_run cofamy transakcję
                transaction.set_rollback(True)
            
    except Exception as e:
        results['success'] = False
        results['errors'].append(f"Krytyczny błąd importu: {str(e)}")
    
    return results
