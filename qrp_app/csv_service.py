"""
Serwis do generowania plików CSV dla pomiarów zgodnie z formatem wymaganym przez zewnętrzną aplikację.
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from django.utils import timezone
from .models import SystemSettings

logger = logging.getLogger(__name__)


def generate_qrp_csv(instance, operator_login):
    """
    Generuje plik CSV dla pomiaru zgodnie z formatem wymaganym przez zewnętrzną aplikację.
    
    Args:
        instance: Instancja modelu Pomiar
        operator_login: Login operatora (format imie.nazwisko, małymi literami) – używany w kolumnie Operator
    
    Returns:
        bool: True jeśli generowanie się powiodło, False w przeciwnym razie
    """
    try:
        # Pobierz ustawienia systemowe
        settings = SystemSettings.load()
        
        # Sprawdź czy eksport CSV jest włączony
        if not settings.csv_export_enabled:
            return False
        
        # Pobierz mapowania
        line_mapping = settings.csv_line_mapping or {}
        machine_mapping = settings.csv_machine_mapping or {}
        inspection_mapping = settings.csv_inspection_mapping or {}
        
        # Przygotuj dane
        data_time = timezone.localtime(instance.data_utworzenia).strftime('%Y-%m-%d %H:%M:%S')
        
        # Pobierz nazwę inspekcji z mapowania (kod rodzaju testu jako klucz)
        inspection_code = str(instance.rodzaj_testu.kod) if instance.rodzaj_testu else ''
        inspection_name = inspection_mapping.get(inspection_code, '')
        
        # Jeśli brak w mapowaniu, użyj nazwy z rodzaju testu
        if not inspection_name:
            inspection_name = instance.get_rodzaj_testu_display() if instance.rodzaj_testu else ''
        # Format: "Lacquer coating CuSO4" (bez " - " przed CuSO4)
        inspection_name = inspection_name.replace(' - CuSO4', ' CuSO4')
        
        inspection_version = 'Quality Control (PL BRZ)'
        attributive_name = 'Test result'
        standard_profile = ''  # Puste zgodnie z wymaganiami
        result = '0'  # Stała wartość
        works_order_no = instance.numer_zlecenia or ''
        check_type_net = str(instance.typ_kontroli) if instance.typ_kontroli else ''
        if check_type_net == 'Standardowe':
            check_type_net = 'Running'
        gauge_name = 'QRP'  # Wymagane przy Running (CheckTypeNet)
        gauge_serial_number = ''  # Puste zgodnie z wymaganiami
        operator = (operator_login or '').strip().lower()
        
        # Mapowanie linii na kod
        linia_nazwa = instance.linia_produkcyjna.nazwa if instance.linia_produkcyjna else ''
        line_code = line_mapping.get(linia_nazwa, '')
        
        # Mapowanie linii na maszynę
        display_machine = machine_mapping.get(linia_nazwa, '')
        
        head = '1'  # Stała wartość
        sample = '1'  # Stała wartość
        position = '1'  # Stała wartość
        area = ''  # Puste zgodnie z wymaganiami
        pallet = ''  # Puste zgodnie z wymaganiami
        internal_coating = ''  # Puste zgodnie z wymaganiami
        external_coating = ''  # Puste zgodnie z wymaganiami
        rim_coating = ''  # Puste zgodnie z wymaganiami
        shell_colour = ''  # Puste zgodnie z wymaganiami
        tab_colour = ''  # Puste zgodnie z wymaganiami
        shell_coil_id = ''  # Puste zgodnie z wymaganiami
        tab_coil_id = ''  # Puste zgodnie z wymaganiami
        bodymaker = ''  # Puste zgodnie z wymaganiami
        spare02 = ''  # Puste zgodnie z wymaganiami
        description = instance.komentarz or ''  # Komentarz w polu Description
        
        # Nagłówki (rozdzielone średnikiem)
        headers = [
            'Date Time',
            'Inspection Name',
            'Inspection Version',
            'Attributive Name',
            'Standard/Profile',
            'Result',
            'WorksOrderNo',
            'CheckTypeNet',
            'Gauge Name',
            'Gauge Serial Number',
            'Operator',
            'LineCode',
            'DisplayMachine',
            'Head',
            'Sample',
            'Position',
            'Area',
            'Pallet',
            'InteralCoating',
            'ExternalCoating',
            'RimCoating',
            'ShellColour',
            'TabColour',
            'ShellCoilID',
            'TabCoilID',
            'Bodymaker',
            'Spare02',
            'Description'
        ]
        
        # Dane wiersza
        row_data = [
            data_time,
            inspection_name,
            inspection_version,
            attributive_name,
            standard_profile,
            result,
            works_order_no,
            check_type_net,
            gauge_name,
            gauge_serial_number,
            operator,
            line_code,
            display_machine,
            head,
            sample,
            position,
            area,
            pallet,
            internal_coating,
            external_coating,
            rim_coating,
            shell_colour,
            tab_colour,
            shell_coil_id,
            tab_coil_id,
            bodymaker,
            spare02,
            description
        ]
        
        # Utwórz folder jeśli nie istnieje
        output_path = Path(settings.csv_output_path)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Nie można utworzyć folderu CSV: {output_path}. Błąd: {e}")
            return False
        
        # Nazwa pliku: QRP[YYYY-MM-DDTHH-MM-SS-fffZ].csv (np. QRP[2026-02-26T15-01-28-910Z].csv)
        now = datetime.now()
        ms = now.microsecond // 1000
        timestamp = now.strftime('%Y-%m-%dT%H-%M-%S') + f'-{ms:03d}Z'
        filename = f'QRP[{timestamp}].csv'
        file_path = output_path / filename
        
        # Zapisz plik z kodowaniem UTF-8 z BOM (dla polskiego Excela)
        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                # Zapisuj nagłówki
                f.write(';'.join(headers) + '\n')
                # Zapisuj dane
                # Zastąp None i None w stringach na puste stringi
                row_data_str = [str(val) if val is not None else '' for val in row_data]
                # Zastąp średniki w wartościach na przecinki (aby nie psuć formatu CSV)
                row_data_clean = [val.replace(';', ',') if isinstance(val, str) else str(val) for val in row_data_str]
                f.write(';'.join(row_data_clean) + '\n')
            
            logger.info(f"Wygenerowano plik CSV: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania pliku CSV: {file_path}. Błąd: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Błąd podczas generowania pliku CSV dla pomiaru #{instance.id}: {e}")
        return False
