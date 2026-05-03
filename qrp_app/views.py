from django.views.generic import TemplateView, View
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
from io import BytesIO
import csv
import os
import uuid
try:
    import requests
except ImportError:
    requests = None
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .models import Rejestrator, LiniaProdukcyjna, RFIDCard, Pomiar, Wada, SystemSettings, SyncLog, RodzajTestu, TypKontroli
from .sync_service import send_to_central_api
from .csv_service import generate_qrp_csv
import re


def validate_username_no_polish_chars(username):
    """
    Sprawdza czy username zawiera tylko litery angielskie (a-z) i kropkę.
    Zwraca True jeśli jest poprawny, False jeśli zawiera polskie znaki.
    """
    # Regex: tylko małe litery angielskie i kropka, format: imie.nazwisko
    pattern = r'^[a-z]+\.[a-z]+$'
    return bool(re.match(pattern, username))


def get_order_number_from_plc(linia):
    """
    Pobiera numer zlecenia z PLC Allen Bradley używając pylogix.
    
    Args:
        linia: Instancja LiniaProdukcyjna z ustawionym ip_plc i zmienna_numer_zlecenia
        
    Returns:
        str: Numer zlecenia jako string, lub None jeśli nie udało się pobrać
    """
    if not linia.ip_plc or not linia.zmienna_numer_zlecenia:
        return None
    
    try:
        from pylogix import PLC  # type: ignore
        
        # Pylogix domyślnie używa portu 44818 dla Allen Bradley
        comm = PLC()
        comm.IPAddress = str(linia.ip_plc)
        
        # Pobierz wartość zmiennej (zakładamy że to STRING lub DINT)
        response = comm.Read(linia.zmienna_numer_zlecenia)
        
        # Sprawdź status odpowiedzi (może być "Success" lub 0 dla sukcesu)
        status_ok = False
        if hasattr(response, 'Status'):
            if response.Status == "Success" or response.Status == 0:
                status_ok = True
        elif hasattr(response, 'Status') and str(response.Status).lower() == 'success':
            status_ok = True
        
        if status_ok and hasattr(response, 'Value') and response.Value is not None:
            # Konwertuj wartość na string
            order_number = str(response.Value).strip()
            if order_number and order_number.lower() not in ['none', 'null', '']:
                return order_number
        
        comm.Close()
    except ImportError:
        # pylogix nie jest zainstalowany
        import sys
        print(f"pylogix nie jest zainstalowany. Zainstaluj: pip install pylogix", file=sys.stderr)
    except Exception as e:
        # Błąd komunikacji z PLC - zwróć None, błąd będzie obsłużony wyżej
        import sys
        print(f"Error reading from PLC {linia.ip_plc} variable {linia.zmienna_numer_zlecenia}: {e}", file=sys.stderr)
        try:
            comm.Close()
        except:
            pass
    
    return None


def create_placeholder_image(text, width=800, height=600):
    img = Image.new('RGB', (width, height), color='#f0f0f0')
    draw = ImageDraw.Draw(img)
    
    try:
        font_size = 40
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    position = ((width - text_width) // 2, (height - text_height) // 2)
    draw.text(position, text, fill='#666666', font=font)
    
    return img


def create_image_icon(width=1920, height=1440):
    """
    Tworzy ładną ikonę aparatu fotograficznego z podpisem "Nie ma zdjęcia"
    jako placeholder gdy nie ma dostępu do kamery.
    """
    # Tło - jasno szare
    img = Image.new('RGB', (width, height), color='#f1f5f9')
    draw = ImageDraw.Draw(img)
    
    # Rozmiar ikony aparatu - większa, wyśrodkowana
    icon_size = int(min(width, height) * 0.25)  # 25% szerokości/wysokości
    icon_x = (width - icon_size) // 2
    icon_y = (height - icon_size) // 2 - 30  # Trochę wyżej, żeby zostawić miejsce na tekst
    
    # Główne ciało aparatu - prostokąt z zaokrąglonymi rogami
    camera_width = int(icon_size * 0.7)
    camera_height = int(icon_size * 0.5)
    camera_x = icon_x + (icon_size - camera_width) // 2
    camera_y = icon_y + int(icon_size * 0.15)
    
    # Zaokrąglone rogi - rysujemy elipsy w rogach
    corner_radius = int(camera_width * 0.08)
    
    # Główne ciało aparatu - czarne z gradientem symulowanym
    draw.rectangle(
        [
            camera_x + corner_radius, camera_y,
            camera_x + camera_width - corner_radius, camera_y + camera_height
        ],
        fill='#1e293b',  # Ciemny szary/czarny
        outline=None
    )
    draw.rectangle(
        [
            camera_x, camera_y + corner_radius,
            camera_x + camera_width, camera_y + camera_height - corner_radius
        ],
        fill='#1e293b',
        outline=None
    )
    
    # Zaokrąglone rogi - elipsy wypełniające rogi
    draw.ellipse(
        [
            camera_x, camera_y,
            camera_x + corner_radius * 2, camera_y + corner_radius * 2
        ],
        fill='#1e293b',
        outline=None
    )
    draw.ellipse(
        [
            camera_x + camera_width - corner_radius * 2, camera_y,
            camera_x + camera_width, camera_y + corner_radius * 2
        ],
        fill='#1e293b',
        outline=None
    )
    draw.ellipse(
        [
            camera_x, camera_y + camera_height - corner_radius * 2,
            camera_x + corner_radius * 2, camera_y + camera_height
        ],
        fill='#1e293b',
        outline=None
    )
    draw.ellipse(
        [
            camera_x + camera_width - corner_radius * 2, camera_y + camera_height - corner_radius * 2,
            camera_x + camera_width, camera_y + camera_height
        ],
        fill='#1e293b',
        outline=None
    )
    
    # Obiektyw - duże koło z metalicznym efektem
    lens_size = int(camera_width * 0.35)
    lens_x = camera_x + (camera_width - lens_size) // 2
    lens_y = camera_y + (camera_height - lens_size) // 2
    
    # Zewnętrzny pierścień obiektywu - ciemniejszy
    draw.ellipse(
        [
            lens_x, lens_y,
            lens_x + lens_size, lens_y + lens_size
        ],
        fill='#0f172a',  # Bardzo ciemny
        outline='#475569',  # Szary
        width=2
    )
    
    # Środek obiektywu - szkło (jasne, z odbiciem)
    inner_lens_size = int(lens_size * 0.65)
    inner_lens_x = lens_x + (lens_size - inner_lens_size) // 2
    inner_lens_y = lens_y + (lens_size - inner_lens_size) // 2
    
    draw.ellipse(
        [
            inner_lens_x, inner_lens_y,
            inner_lens_x + inner_lens_size, inner_lens_y + inner_lens_size
        ],
        fill='#334155',  # Ciemnoszary
        outline=None
    )
    
    # Odbicie na szkle - efekt błysku
    reflection_size = int(inner_lens_size * 0.4)
    reflection_x = inner_lens_x + int(inner_lens_size * 0.25)
    reflection_y = inner_lens_y + int(inner_lens_size * 0.25)
    draw.ellipse(
        [
            reflection_x, reflection_y,
            reflection_x + reflection_size, reflection_y + reflection_size
        ],
        fill='#64748b',  # Jaśniejszy szary
        outline=None
    )
    
    # Błyskawica (flash) - mały prostokąt w prawym górnym rogu
    flash_size = int(camera_width * 0.12)
    flash_x = camera_x + int(camera_width * 0.75)
    flash_y = camera_y + int(camera_height * 0.15)
    draw.rectangle(
        [
            flash_x, flash_y,
            flash_x + flash_size, flash_y + flash_size
        ],
        fill='#f8fafc',  # Biały
        outline='#cbd5e1',  # Szara obwódka
        width=1
    )
    
    # Wewnętrzny element flasha
    draw.ellipse(
        [
            flash_x + 2, flash_y + 2,
            flash_x + flash_size - 2, flash_y + flash_size - 2
        ],
        fill='#e2e8f0',
        outline=None
    )
    
    # Górna część aparatu (grip/viewfinder)
    grip_width = int(camera_width * 0.25)
    grip_height = int(camera_height * 0.25)
    grip_x = camera_x + (camera_width - grip_width) // 2
    grip_y = camera_y - grip_height
    
    draw.rectangle(
        [
            grip_x, grip_y,
            grip_x + grip_width, grip_y + grip_height
        ],
        fill='#1e293b',
        outline=None
    )
    
    # Viewfinder (wizjer)
    viewfinder_size = int(grip_width * 0.4)
    viewfinder_x = grip_x + (grip_width - viewfinder_size) // 2
    viewfinder_y = grip_y + (grip_height - viewfinder_size) // 2
    
    draw.ellipse(
        [
            viewfinder_x, viewfinder_y,
            viewfinder_x + viewfinder_size, viewfinder_y + viewfinder_size
        ],
        fill='#0f172a',
        outline='#475569',
        width=1
    )
    
    # Tekst "Nie ma zdjęcia"
    try:
        # Próbuj załadować font systemowy
        try:
            font_size = int(min(width, height) * 0.035)
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
        font_size = 20
    
    text = "Nie ma zdjęcia"
    # Oblicz szerokość tekstu
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (width - text_width) // 2
    text_y = icon_y + icon_size + 20
    
    # Cień tekstu (opcjonalnie)
    draw.text((text_x + 1, text_y + 1), text, font=font, fill='#cbd5e1')
    # Główny tekst
    draw.text((text_x, text_y), text, font=font, fill='#64748b')
    
    return img


def download_image_from_url(url, timeout=5):
    """Pobiera obraz z URL i zwraca obiekt PIL Image"""
    if requests is None:
        print("Module 'requests' is not installed. Cannot download image from URL.")
        return None
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        return img
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return None


def _try_register_pdf_font():
    """
    Rejestruje font TTF z obsługą polskich znaków dla ReportLab.
    Nie dodajemy binarek do repo, więc próbujemy typowych ścieżek systemowych.
    Zwraca (regular_font_name, bold_font_name) albo (None, None) jeśli brak fontu.
    """
    regular_name = "QRPUnicode"
    bold_name = "QRPUnicode-Bold"

    # Jeśli już zarejestrowane (np. w workerze), nie rób nic
    if regular_name in pdfmetrics.getRegisteredFontNames():
        return regular_name, (bold_name if bold_name in pdfmetrics.getRegisteredFontNames() else None)

    candidates_regular = [
        # Linux (najczęściej)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    candidates_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]

    regular_path = next((p for p in candidates_regular if os.path.exists(p)), None)
    if not regular_path:
        return None, None

    try:
        pdfmetrics.registerFont(TTFont(regular_name, regular_path))
    except Exception:
        return None, None

    bold_path = next((p for p in candidates_bold if os.path.exists(p)), None)
    if bold_path:
        try:
            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
        except Exception:
            bold_name = None
    else:
        bold_name = None

    return regular_name, bold_name


class RFIDLoginView(TemplateView):
    template_name = 'qrp_app/rfid_login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('qrp_app:measurement')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Sprawdź czy jest aktywna linia z hostname (z middleware)
        rejestrator = None
        if hasattr(self.request, 'active_line') and self.request.active_line:
            rejestrator = self.request.active_line.rejestrator
        elif hasattr(self.request, 'active_lines') and self.request.active_lines:
            # Jeśli jest wiele linii, weź pierwszą
            first_line = self.request.active_lines[0] if self.request.active_lines else None
            if first_line:
                rejestrator = first_line.rejestrator
        
        # Jeśli nie ma rejestratora z hostname, spróbuj znaleźć aktywny rejestrator
        if not rejestrator:
            rejestrator = Rejestrator.objects.filter(aktywny=True).first()
        
        # Ustaw flagę czy rejestrator jest dla KJ (domyślnie True jeśli nie ma rejestratora)
        context['rejestrator_dla_kj'] = rejestrator.dla_kj if rejestrator else True
        
        return context


@method_decorator(login_required, name='dispatch')
class MeasurementView(TemplateView):
    template_name = 'qrp_app/measurement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Jeśli jest routing przez DNS (middleware), użyj linii z DNS, w przeciwnym razie wszystkie aktywne
        if hasattr(self.request, 'active_lines') and self.request.active_lines:
            linie = LiniaProdukcyjna.objects.filter(
                id__in=[l.id for l in self.request.active_lines]
            ).select_related('rejestrator')
        else:
            linie = LiniaProdukcyjna.objects.filter(aktywna=True).select_related('rejestrator')
        
        context['linie'] = linie
        context['auto_select_line'] = linie.count() == 1
        context['ostatni_pomiar'] = Pomiar.objects.filter(uzytkownik=self.request.user).select_related('linia_produkcyjna__rejestrator', 'uzytkownik', 'rodzaj_testu', 'typ_kontroli').order_by('-data_utworzenia').first()
        # Pobierz aktywnych rejestratorów z url_kamery dla automatycznego podglądu
        context['rejestratory'] = Rejestrator.objects.filter(aktywny=True).exclude(url_kamery__isnull=True).exclude(url_kamery='').prefetch_related('dostepne_typy_kontroli', 'dostepne_rodzaje_testu')
        
        # Pobierz opcje na podstawie rejestratora (jeśli jest tylko jeden rejestrator lub jedna linia)
        domyslny_typ_kontroli_id = None
        domyslny_rodzaj_testu_id = None
        
        if linie.count() == 1:
            rejestrator = linie.first().rejestrator
            # Sprawdź czy rejestrator ma przypisane opcje
            from .models import RejestratorTypKontroli, RejestratorRodzajTestu
            
            # Pobierz domyślne wartości z rejestratora
            if rejestrator.domyslny_typ_kontroli:
                domyslny_typ_kontroli_id = rejestrator.domyslny_typ_kontroli.id
            if rejestrator.domyslny_rodzaj_testu:
                domyslny_rodzaj_testu_id = rejestrator.domyslny_rodzaj_testu.id
            
            rejestrator_typy = RejestratorTypKontroli.objects.filter(
                rejestrator=rejestrator,
                aktywny=True
            ).select_related('typ_kontroli').order_by('kolejnosc', 'typ_kontroli__nazwa')
            
            if rejestrator_typy.exists():
                dostepne_typy = [rt.typ_kontroli for rt in rejestrator_typy if rt.typ_kontroli.aktywny]
            else:
                dostepne_typy = TypKontroli.objects.filter(aktywny=True).order_by('kolejnosc', 'kod')
            
            rejestrator_rodzaje = RejestratorRodzajTestu.objects.filter(
                rejestrator=rejestrator,
                aktywny=True
            ).select_related('rodzaj_testu').order_by('kolejnosc', 'rodzaj_testu__kod')
            
            if rejestrator_rodzaje.exists():
                dostepne_rodzaje = [rr.rodzaj_testu for rr in rejestrator_rodzaje if rr.rodzaj_testu.aktywny]
            else:
                dostepne_rodzaje = RodzajTestu.objects.filter(aktywny=True).order_by('kolejnosc', 'kod')
        else:
            # Jeśli więcej linii, pokaż wszystkie aktywne opcje
            # Ale spróbuj pobrać domyślne wartości z pierwszej linii, jeśli są dostępne
            if linie.exists():
                first_rejestrator = linie.first().rejestrator
                if first_rejestrator:
                    if first_rejestrator.domyslny_typ_kontroli:
                        domyslny_typ_kontroli_id = first_rejestrator.domyslny_typ_kontroli.id
                    if first_rejestrator.domyslny_rodzaj_testu:
                        domyslny_rodzaj_testu_id = first_rejestrator.domyslny_rodzaj_testu.id
            dostepne_typy = TypKontroli.objects.filter(aktywny=True)
            dostepne_rodzaje = RodzajTestu.objects.filter(aktywny=True)
        
        context['typy_kontroli'] = dostepne_typy if isinstance(dostepne_typy, list) else dostepne_typy.order_by('kolejnosc', 'kod')
        context['rodzaje_testu'] = dostepne_rodzaje if isinstance(dostepne_rodzaje, list) else dostepne_rodzaje.order_by('kolejnosc', 'kod')
        context['domyslny_typ_kontroli_id'] = domyslny_typ_kontroli_id
        context['domyslny_rodzaj_testu_id'] = domyslny_rodzaj_testu_id
        return context


@method_decorator(login_required, name='dispatch')
class DefectView(TemplateView):
    template_name = 'qrp_app/defect.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Jeśli jest routing przez DNS (middleware), użyj linii z DNS, w przeciwnym razie wszystkie aktywne
        if hasattr(self.request, 'active_lines') and self.request.active_lines:
            linie = LiniaProdukcyjna.objects.filter(
                id__in=[l.id for l in self.request.active_lines]
            ).select_related('rejestrator')
        else:
            linie = LiniaProdukcyjna.objects.filter(aktywna=True).select_related('rejestrator')
        
        context['linie'] = linie
        context['auto_select_line'] = linie.count() == 1
        context['ostatnia_wada'] = Wada.objects.filter(uzytkownik=self.request.user).select_related('linia_produkcyjna__rejestrator', 'uzytkownik', 'typ_kontroli').order_by('-data_utworzenia').first()
        # Pobierz aktywnych rejestratorów z url_kamery dla automatycznego podglądu
        context['rejestratory'] = Rejestrator.objects.filter(aktywny=True).exclude(url_kamery__isnull=True).exclude(url_kamery='').prefetch_related('dostepne_typy_kontroli', 'dostepne_rodzaje_testu')
        
        # Pobierz opcje na podstawie rejestratora (jeśli jest tylko jeden rejestrator lub jedna linia)
        if linie.count() == 1:
            from .models import RejestratorTypKontroli
            
            rejestrator = linie.first().rejestrator
            # Sprawdź czy rejestrator ma przypisane opcje
            rejestrator_typy = RejestratorTypKontroli.objects.filter(
                rejestrator=rejestrator,
                aktywny=True
            ).select_related('typ_kontroli').order_by('kolejnosc', 'typ_kontroli__nazwa')
            
            if rejestrator_typy.exists():
                dostepne_typy = [rt.typ_kontroli for rt in rejestrator_typy if rt.typ_kontroli.aktywny]
            else:
                dostepne_typy = TypKontroli.objects.filter(aktywny=True)
        else:
            # Jeśli więcej linii, pokaż wszystkie aktywne opcje
            dostepne_typy = TypKontroli.objects.filter(aktywny=True)
        
        context['typy_kontroli'] = dostepne_typy if isinstance(dostepne_typy, list) else dostepne_typy.order_by('kolejnosc', 'kod')
        return context


@method_decorator(login_required, name='dispatch')
class ArchiveView(TemplateView):
    template_name = 'qrp_app/archive.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['linie'] = LiniaProdukcyjna.objects.filter(aktywna=True).select_related('rejestrator')
        
        # Pobierz wszystkie pomiary i wady (z prefetch dla RFID card aby uniknąć N+1)
        pomiary = Pomiar.objects.select_related('linia_produkcyjna__rejestrator', 'uzytkownik', 'rodzaj_testu', 'typ_kontroli').prefetch_related('uzytkownik__rfid_card').order_by('-data_utworzenia')
        wady = Wada.objects.select_related('linia_produkcyjna__rejestrator', 'uzytkownik', 'typ_kontroli').prefetch_related('uzytkownik__rfid_card').order_by('-data_utworzenia')
        
        def safe_kj(rec):
            try:
                return (getattr(getattr(rec.uzytkownik, 'rfid_card', None), 'numer_kj', None) or '') if getattr(rec, 'uzytkownik', None) else ''
            except Exception:
                return ''
        
        # Połącz pomiary i wady w jedną listę z bezpiecznym numerem KJ, posortowaną po data_utworzenia
        all_records = []
        for pomiar in pomiary:
            all_records.append(('measurement', pomiar, safe_kj(pomiar)))
        for wada in wady:
            all_records.append(('defect', wada, safe_kj(wada)))
        
        # Posortuj po data_utworzenia – ostatnio zapisane (najnowsze) na górze; brak daty na końcu
        from datetime import datetime as dt_min
        all_records.sort(
            key=lambda x: (1 if x[1].data_utworzenia else 0, x[1].data_utworzenia or dt_min.min),
            reverse=True
        )
        
        # Przekaż połączoną listę do template
        context['all_records'] = all_records
        context['pomiary'] = pomiary
        context['wady'] = wady
        context['total_count'] = len(all_records)
        context['pomiary_count'] = pomiary.count()
        context['wady_count'] = wady.count()
        
        # Ustawienia synchronizacji
        try:
            sync_settings = SystemSettings.load()
            context['show_sync_status'] = sync_settings.show_sync_status
            context['show_sync_column'] = sync_settings.show_sync_column
            
            # Ostatni log synchronizacji dla statusu
            last_log = SyncLog.objects.order_by('-timestamp').first()
            context['last_sync_success'] = last_log.is_success if last_log else None
        except Exception:
            context['show_sync_status'] = False
            context['show_sync_column'] = False
            context['last_sync_success'] = None
        
        # Pobierz typy kontroli dla filtrów
        context['typy_kontroli'] = TypKontroli.objects.filter(aktywny=True).order_by('kolejnosc', 'kod')
        
        return context


@method_decorator(login_required, name='dispatch')
class HelpView(TemplateView):
    template_name = 'qrp_app/help.html'


@method_decorator(csrf_exempt, name='dispatch')
class RFIDLoginAPI(View):
    def post(self, request):
        try:
            rfid_code = request.POST.get('rfid_code', '').strip()
            
            if not rfid_code:
                return JsonResponse({'success': False, 'message': 'Brak kodu RFID'}, status=400)
            
            try:
                rfid_card = RFIDCard.objects.get(card_id=rfid_code, aktywna=True)
                user = rfid_card.user
                
                if user.is_active:
                    login(request, user)
                    return JsonResponse({
                        'success': True,
                        'user': user.username,
                        'redirect': '/measurement/'
                    })
                else:
                    return JsonResponse({'success': False, 'message': 'Konto użytkownika jest nieaktywne'}, status=403)
            except RFIDCard.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'rfid_to_register': rfid_code
                })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class RFIDRegisterAPI(View):
    def post(self, request):
        try:
            rfid_code = request.POST.get('rfid_code', '').strip()
            name = request.POST.get('name', '').strip()
            kj_number = request.POST.get('kj_number', '').strip()
            
            if not rfid_code or not name:
                return JsonResponse({'success': False, 'message': 'Wymagane pola: rfid_code i name'}, status=400)
            
            # Sprawdź czy rejestrator wymaga numeru KJ
            rejestrator_dla_kj = True  # Domyślnie True
            if hasattr(request, 'active_line') and request.active_line:
                rejestrator_dla_kj = request.active_line.rejestrator.dla_kj
            elif hasattr(request, 'active_lines') and request.active_lines:
                first_line = request.active_lines[0] if request.active_lines else None
                if first_line:
                    rejestrator_dla_kj = first_line.rejestrator.dla_kj
            else:
                # Jeśli nie ma rejestratora z hostname, sprawdź aktywny rejestrator
                rejestrator = Rejestrator.objects.filter(aktywny=True).first()
                if rejestrator:
                    rejestrator_dla_kj = rejestrator.dla_kj
            
            # Jeśli rejestrator jest dla KJ, wymagaj numeru KJ
            if rejestrator_dla_kj and not kj_number:
                return JsonResponse({'success': False, 'message': 'Podaj numer KJ'}, status=400)
            
            if RFIDCard.objects.filter(card_id=rfid_code).exists():
                return JsonResponse({'success': False, 'message': 'Karta już zarejestrowana'}, status=400)
            
            if User.objects.filter(username=name).exists():
                return JsonResponse({'success': False, 'message': 'Użytkownik o tym loginie już istnieje'}, status=400)
            
            # Walidacja: tylko litery angielskie, bez polskich znaków
            if not validate_username_no_polish_chars(name):
                return JsonResponse({
                    'success': False, 
                    'message': 'Login może zawierać tylko litery angielskie (a-z) i kropkę. Format: imie.nazwisko'
                }, status=400)
            
            name_parts = name.split('.')
            first_name = name_parts[0].capitalize() if len(name_parts) > 0 else name.capitalize()
            last_name = name_parts[1].capitalize() if len(name_parts) > 1 else ''
            
            user = User.objects.create_user(
                username=name,
                first_name=first_name,
                last_name=last_name,
            )
            
            rfid_card = RFIDCard.objects.create(
                user=user,
                card_id=rfid_code,
                numer_kj=kj_number if kj_number else None
            )
            
            login(request, user)
            
            return JsonResponse({
                'success': True,
                'user': user.username
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('qrp_app:rfid_login')
    
    def get(self, request):
        logout(request)
        return redirect('qrp_app:rfid_login')


@method_decorator(login_required, name='dispatch')
class OrderNumberAPI(View):
    """
    Endpoint do pobierania numeru zlecenia z PLC dla wybranej linii.
    GET /api/order-number/?line_id=123
    """
    def get(self, request):
        try:
            linia_id = request.GET.get('line_id')
            if not linia_id:
                return JsonResponse({'success': False, 'message': 'Brak ID linii'}, status=400)
            
            try:
                linia = LiniaProdukcyjna.objects.get(id=linia_id, aktywna=True)
            except LiniaProdukcyjna.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Nieprawidłowa linia produkcyjna'}, status=400)
            
            # Spróbuj pobrać numer zlecenia z PLC
            order_number = get_order_number_from_plc(linia)
            
            if order_number:
                return JsonResponse({
                    'success': True,
                    'order_number': order_number,
                    'source': 'plc'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Nie udało się pobrać numeru zlecenia z PLC. Sprawdź połączenie i konfigurację.',
                    'source': 'error'
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Błąd podczas pobierania numeru zlecenia: {str(e)}'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class MeasurementAPI(View):
    def post(self, request):
        try:
            linia_id = request.POST.get('line')
            control_type_id = request.POST.get('controlType')
            test_type_id = request.POST.get('testType')
            comment = request.POST.get('comment', '').strip()
            order_number = request.POST.get('orderNumber', '').strip()
            
            if not linia_id:
                return JsonResponse({'success': False, 'message': 'Wybierz linię produkcyjną'}, status=400)
            
            if not test_type_id:
                return JsonResponse({'success': False, 'message': 'Wybierz rodzaj testu'}, status=400)
            
            try:
                linia = LiniaProdukcyjna.objects.get(id=linia_id, aktywna=True)
            except LiniaProdukcyjna.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Nieprawidłowa linia produkcyjna'}, status=400)
            
            try:
                rodzaj_testu = RodzajTestu.objects.get(id=test_type_id, aktywny=True)
            except RodzajTestu.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Nieprawidłowy rodzaj testu'}, status=400)
            
            if not control_type_id:
                return JsonResponse({'success': False, 'message': 'Wybierz typ kontroli'}, status=400)
            
            try:
                typ_kontroli = TypKontroli.objects.get(id=control_type_id, aktywny=True)
            except TypKontroli.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Nieprawidłowy typ kontroli'}, status=400)
            
            # Jeśli numer zlecenia nie został przekazany ręcznie, spróbuj pobrać z PLC
            # Nie blokuj jeśli nie uda się pobrać - użytkownik może wpisać ręcznie
            if not order_number:
                try:
                    order_number = get_order_number_from_plc(linia)
                    if order_number:
                        order_number = order_number.strip()
                except Exception:
                    pass  # Ignoruj błędy PLC - nie blokuj zapisu
            
            # Walidacja: numer zlecenia jest wymagany
            if not order_number:
                return JsonResponse({'success': False, 'message': 'Numer zlecenia jest wymagany'}, status=400)
            
            # Spróbuj pobrać obraz z URL kamery (używaj kamery z rejestratora, jeśli nie ma na linii)
            # Nie blokuj jeśli nie uda się pobrać - użyj placeholder
            img = None
            try:
                camera_url = linia.rejestrator.url_kamery if linia.rejestrator and linia.rejestrator.url_kamery else (linia.url_kamery if hasattr(linia, 'url_kamery') and linia.url_kamery else None)
                if camera_url:
                    # Dodaj timestamp do URL, aby uniknąć cache
                    from datetime import datetime
                    if 'timestamp=' in camera_url:
                        # Zastąp istniejący timestamp
                        parsed = urlparse(camera_url)
                        query_params = parse_qs(parsed.query)
                        query_params['timestamp'] = [str(int(datetime.now().timestamp()))]
                        new_query = urlencode(query_params, doseq=True)
                        camera_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
                    else:
                        # Dodaj timestamp
                        separator = '&' if '?' in camera_url else '?'
                        camera_url = f"{camera_url}{separator}timestamp={int(datetime.now().timestamp())}"
                    
                    img = download_image_from_url(camera_url)
            except Exception:
                pass  # Ignoruj błędy kamery - użyj placeholder
            
            # Jeśli nie udało się pobrać, użyj ikony symulującej zdjęcie
            if img is None:
                try:
                    img = create_image_icon()
                except Exception:
                    # Jeśli nawet ikona się nie powiedzie, stwórz minimalny obraz
                    img = Image.new('RGB', (800, 600), color='#e5e7eb')
            
            os.makedirs(settings.MEDIA_ROOT / 'pomiary', exist_ok=True)
            unique_id = str(uuid.uuid4())[:8]
            img_filename = f'pomiar_{request.user.id}_{unique_id}.png'
            img_path = settings.MEDIA_ROOT / 'pomiary' / img_filename
            
            img.save(img_path)
            
            pomiar = Pomiar.objects.create(
                linia_produkcyjna=linia,
                uzytkownik=request.user,
                typ_kontroli=typ_kontroli,
                rodzaj_testu=rodzaj_testu,
                numer_zlecenia=order_number if order_number else None,
                komentarz=comment if comment else None,
                zdjecie=f'pomiary/{img_filename}'
            )
            
            # Login operatora (imie.nazwisko, małymi literami) – do kolumny Operator w CSV
            operator_login = request.user.username or ''
            
            # Próbuj zsynchronizować w tle (nie blokuj odpowiedzi)
            try:
                send_to_central_api(pomiar)
            except Exception:
                pass  # Ignoruj błędy synchronizacji - nie powinny blokować zapisu rekordu
            
            # Próbuj wygenerować plik CSV (nie blokuj odpowiedzi)
            try:
                generate_qrp_csv(pomiar, operator_login)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Błąd podczas generowania pliku CSV dla pomiaru #{pomiar.id}: {e}")
                # Nie przerywaj działania - CSV to dodatkowa funkcjonalność
            
            return JsonResponse({
                'success': True,
                'message': 'Pomiar został zarejestrowany',
                'id': pomiar.id,
                'record': {
                    'id': pomiar.id,
                    'zdjecie_url': pomiar.zdjecie.url if pomiar.zdjecie else None,
                    'data': timezone.localtime(pomiar.data_utworzenia).strftime('%Y-%m-%d %H:%M:%S'),
                    'linia': pomiar.linia_produkcyjna.nazwa,
                    'typ_kontroli': str(pomiar.typ_kontroli) if pomiar.typ_kontroli else '',
                    'rodzaj_testu': pomiar.get_rodzaj_testu_display(),
                    'numer_zlecenia': pomiar.numer_zlecenia or '',
                    'komentarz': pomiar.komentarz or ''
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class DefectAPI(View):
    def post(self, request):
        try:
            linia_id = request.POST.get('line')
            defect_description = request.POST.get('defectDescription', '').strip()
            comment = request.POST.get('comment', '').strip()
            order_number = request.POST.get('orderNumber', '').strip()
            
            if not linia_id:
                return JsonResponse({'success': False, 'message': 'Wybierz linię produkcyjną'}, status=400)
            
            if not defect_description:
                return JsonResponse({'success': False, 'message': 'Opisz wadę'}, status=400)
            
            try:
                linia = LiniaProdukcyjna.objects.get(id=linia_id, aktywna=True)
            except LiniaProdukcyjna.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Nieprawidłowa linia produkcyjna'}, status=400)
            
            # Pobierz typ kontroli (wymagany)
            control_type_id = request.POST.get('controlType')
            if not control_type_id:
                return JsonResponse({'success': False, 'message': 'Wybierz typ kontroli'}, status=400)
            
            try:
                typ_kontroli = TypKontroli.objects.get(id=control_type_id, aktywny=True)
            except TypKontroli.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Nieprawidłowy typ kontroli'}, status=400)
            
            # Jeśli numer zlecenia nie został przekazany ręcznie, spróbuj pobrać z PLC
            # Nie blokuj jeśli nie uda się pobrać - użytkownik może wpisać ręcznie
            if not order_number:
                try:
                    order_number = get_order_number_from_plc(linia)
                    if order_number:
                        order_number = order_number.strip()
                except Exception:
                    pass  # Ignoruj błędy PLC - nie blokuj zapisu
            
            # Walidacja: numer zlecenia jest wymagany
            if not order_number:
                return JsonResponse({'success': False, 'message': 'Numer zlecenia jest wymagany'}, status=400)
            
            # Spróbuj pobrać obraz z URL kamery (używaj kamery z rejestratora, jeśli nie ma na linii)
            # Nie blokuj jeśli nie uda się pobrać - użyj placeholder
            img = None
            try:
                camera_url = linia.rejestrator.url_kamery if linia.rejestrator and linia.rejestrator.url_kamery else (linia.url_kamery if hasattr(linia, 'url_kamery') and linia.url_kamery else None)
                if camera_url:
                    # Dodaj timestamp do URL, aby uniknąć cache
                    from datetime import datetime
                    if 'timestamp=' in camera_url:
                        # Zastąp istniejący timestamp
                        parsed = urlparse(camera_url)
                        query_params = parse_qs(parsed.query)
                        query_params['timestamp'] = [str(int(datetime.now().timestamp()))]
                        new_query = urlencode(query_params, doseq=True)
                        camera_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
                    else:
                        # Dodaj timestamp
                        separator = '&' if '?' in camera_url else '?'
                        camera_url = f"{camera_url}{separator}timestamp={int(datetime.now().timestamp())}"
                    
                    img = download_image_from_url(camera_url)
            except Exception:
                pass  # Ignoruj błędy kamery - użyj placeholder
            
            # Jeśli nie udało się pobrać, użyj ikony symulującej zdjęcie
            if img is None:
                try:
                    img = create_image_icon()
                except Exception:
                    # Jeśli nawet ikona się nie powiedzie, stwórz minimalny obraz
                    img = Image.new('RGB', (800, 600), color='#e5e7eb')
            
            os.makedirs(settings.MEDIA_ROOT / 'wady', exist_ok=True)
            unique_id = str(uuid.uuid4())[:8]
            img_filename = f'wada_{request.user.id}_{unique_id}.png'
            img_path = settings.MEDIA_ROOT / 'wady' / img_filename
            
            img.save(img_path)
            
            wada = Wada.objects.create(
                linia_produkcyjna=linia,
                uzytkownik=request.user,
                typ_kontroli=typ_kontroli,
                opis_wady=defect_description,
                numer_zlecenia=order_number if order_number else None,
                komentarz=comment if comment else None,
                zdjecie=f'wady/{img_filename}'
            )
            
            # Próbuj zsynchronizować w tle (nie blokuj odpowiedzi)
            try:
                send_to_central_api(wada)
            except Exception:
                pass  # Ignoruj błędy synchronizacji - nie powinny blokować zapisu rekordu
            
            return JsonResponse({
                'success': True,
                'message': 'Wada została zarejestrowana',
                'id': wada.id,
                'record': {
                    'id': wada.id,
                    'zdjecie_url': wada.zdjecie.url if wada.zdjecie else None,
                    'data': timezone.localtime(wada.data_utworzenia).strftime('%Y-%m-%d %H:%M:%S'),
                    'linia': wada.linia_produkcyjna.nazwa,
                    'typ_kontroli': str(wada.typ_kontroli) if wada.typ_kontroli else '',
                    'opis_wady': wada.opis_wady,
                    'numer_zlecenia': wada.numer_zlecenia or '',
                    'komentarz': wada.komentarz or ''
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class ExportCSVView(View):
    def get(self, request):
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        
        # Generuj timestamp dla nazwy pliku (format: YYYYMMDD_HHMMSS)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'qrp_{timestamp}.csv'
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Sprawdź czy są przekazane ID rekordów do eksportu (filtrowane wyniki)
        ids_param = request.GET.getlist('ids')
        
        if ids_param:
            # Eksportuj tylko wybrane rekordy
            measurement_ids = []
            defect_ids = []
            
            for id_str in ids_param:
                if id_str.startswith('measurement_'):
                    measurement_ids.append(int(id_str.replace('measurement_', '')))
                elif id_str.startswith('defect_'):
                    defect_ids.append(int(id_str.replace('defect_', '')))
            
            pomiary = Pomiar.objects.filter(id__in=measurement_ids).select_related('linia_produkcyjna__rejestrator', 'uzytkownik', 'rodzaj_testu', 'typ_kontroli').order_by('-data_utworzenia')
            wady = Wada.objects.filter(id__in=defect_ids).select_related('linia_produkcyjna__rejestrator', 'uzytkownik', 'typ_kontroli').order_by('-data_utworzenia')
        else:
            # Eksportuj całą bazę
            pomiary = Pomiar.objects.select_related('linia_produkcyjna__rejestrator', 'uzytkownik', 'rodzaj_testu', 'typ_kontroli').order_by('-data_utworzenia')
            wady = Wada.objects.select_related('linia_produkcyjna__rejestrator', 'uzytkownik', 'typ_kontroli').order_by('-data_utworzenia')
        
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['QC PLATFORM'])
        writer.writerow(['Data wygenerowania:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        writer.writerow(['Typ', 'ID', 'Data', 'Linia', 'Operator', 'Typ kontroli', 'Zlecenie', 'Opis/Test', 'Komentarz'])
        
        for pomiar in pomiary:
            writer.writerow([
                'Pomiar',
                pomiar.id,
                timezone.localtime(pomiar.data_utworzenia).strftime('%Y-%m-%d %H:%M:%S'),
                pomiar.linia_produkcyjna.nazwa,
                pomiar.uzytkownik.username if pomiar.uzytkownik else '',
                str(pomiar.typ_kontroli) if pomiar.typ_kontroli else '',
                pomiar.numer_zlecenia or '',
                pomiar.get_rodzaj_testu_display(),
                pomiar.komentarz or ''
            ])
        
        for wada in wady:
            writer.writerow([
                'Wada',
                wada.id,
                timezone.localtime(wada.data_utworzenia).strftime('%Y-%m-%d %H:%M:%S'),
                wada.linia_produkcyjna.nazwa,
                wada.uzytkownik.username if wada.uzytkownik else '',
                str(wada.typ_kontroli) if wada.typ_kontroli else '',
                wada.numer_zlecenia or '',
                wada.opis_wady,
                wada.komentarz or ''
            ])
        
        return response


@method_decorator(login_required, name='dispatch')
class ExportPDFView(View):
    def get(self, request, record_type, record_id):
        if record_type == 'measurement':
            record = get_object_or_404(Pomiar, id=record_id)
            title = f"Raport Pomiaru #{record.id}"
        elif record_type == 'defect':
            record = get_object_or_404(Wada, id=record_id)
            title = f"Raport Wady #{record.id}"
        else:
            return HttpResponseNotFound("Nieprawidłowy typ rekordu")
        
        response = HttpResponse(content_type='application/pdf; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{record_type}_{record_id}.pdf"'
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=2*cm, 
            leftMargin=2*cm, 
            topMargin=2*cm, 
            bottomMargin=2*cm,
            title=title,
            author='QRP QC Platform'
        )
        
        story = []
        styles = getSampleStyleSheet()

        unicode_font, unicode_bold_font = _try_register_pdf_font()
        
        # Używamy czcionek Unicode jeśli dostępne, w przeciwnym razie używamy wbudowanych
        # czcionek ReportLab, które lepiej obsługują polskie znaki w Edge
        if unicode_font:
            base_font = unicode_font
            base_bold_font = unicode_bold_font or unicode_font
        else:
            # ReportLab ma wbudowane czcionki z obsługą Unicode
            # Helvetica nie obsługuje polskich znaków, więc używamy Times-Roman jako fallback
            # które mają lepszą obsługę Unicode w niektórych przeglądarkach
            base_font = "Times-Roman"
            base_bold_font = "Times-Bold"
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=base_bold_font,
        )
        
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Styl dla komórek z wartościami - umożliwia zawijanie tekstu
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontName=base_font,
            fontSize=10,
            leading=12,
            wordWrap='CJK',
            leftIndent=0,
            rightIndent=0,
        )
        
        # Styl dla etykiet (pierwsza kolumna)
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontName=base_font,
            fontSize=10,
            leading=12,
            leftIndent=0,
            rightIndent=0,
        )
        
        data = [
            [Paragraph('<b>Pole</b>', label_style), Paragraph('<b>Wartość</b>', label_style)],
        ]
        
        def make_value_cell(value):
            """Funkcja pomocnicza do tworzenia komórki z zawijaniem tekstu"""
            if not value:
                return ''
            # Używamy Paragraph dla wszystkich wartości, aby umożliwić zawijanie
            # Escapujemy HTML specjalne znaki, ale zachowujemy polskie znaki Unicode
            safe_value = (str(value)
                         .replace('&', '&amp;')
                         .replace('<', '&lt;')
                         .replace('>', '&gt;')
                         .replace('"', '&quot;')
                         .replace("'", '&#x27;'))
            return Paragraph(safe_value, value_style)
        
        def make_label_cell(label):
            """Funkcja pomocnicza do tworzenia komórki etykiety"""
            return Paragraph(str(label), label_style)
        
        if record_type == 'measurement':
            data.extend([
                [make_label_cell('Data'), make_value_cell(timezone.localtime(record.data_utworzenia).strftime('%Y-%m-%d %H:%M:%S'))],
                [make_label_cell('Linia produkcyjna'), make_value_cell(record.linia_produkcyjna.nazwa)],
                [make_label_cell('Operator'), make_value_cell(record.uzytkownik.username if record.uzytkownik else '')],
                [make_label_cell('Typ kontroli'), make_value_cell(str(record.typ_kontroli) if record.typ_kontroli else '')],
                [make_label_cell('Rodzaj testu'), make_value_cell(record.get_rodzaj_testu_display())],
                [make_label_cell('Numer zlecenia'), make_value_cell(record.numer_zlecenia or '')],
                [make_label_cell('Komentarz'), make_value_cell(record.komentarz or '')],
            ])
        else:
            data.extend([
                [make_label_cell('Data'), make_value_cell(timezone.localtime(record.data_utworzenia).strftime('%Y-%m-%d %H:%M:%S'))],
                [make_label_cell('Linia produkcyjna'), make_value_cell(record.linia_produkcyjna.nazwa)],
                [make_label_cell('Operator'), make_value_cell(record.uzytkownik.username if record.uzytkownik else '')],
                [make_label_cell('Typ kontroli'), make_value_cell(str(record.typ_kontroli) if record.typ_kontroli else '')],
                [make_label_cell('Opis wady'), make_value_cell(record.opis_wady)],
                [make_label_cell('Numer zlecenia'), make_value_cell(record.numer_zlecenia or '')],
                [make_label_cell('Komentarz'), make_value_cell(record.komentarz or '')],
            ])
        
        table = Table(data, colWidths=[5*cm, 12*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), base_bold_font),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 1), (-1, -1), base_font),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 1*cm))
        
        if record.zdjecie:
            img_path = settings.MEDIA_ROOT / str(record.zdjecie)
            if img_path.exists():
                try:
                    img = ReportLabImage(str(img_path), width=15*cm, height=10*cm, kind='proportional')
                    story.append(Paragraph('<b>Zdjęcie:</b>', ParagraphStyle(
                        'PhotoHeader',
                        parent=styles['Heading2'],
                        fontName=base_bold_font,
                    )))
                    story.append(Spacer(1, 0.3*cm))
                    story.append(img)
                except:
                    story.append(Paragraph('<b>Zdjęcie:</b> Nie udało się załadować obrazu', ParagraphStyle(
                        'PhotoError',
                        parent=styles['Normal'],
                        fontName=base_font,
                    )))
        
        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response


@method_decorator(login_required, name='dispatch')
class SyncStatusAPI(View):
    """API endpoint do pobierania statusu synchronizacji"""
    
    def get(self, request):
        try:
            settings_obj = SystemSettings.load()
            
            # Sprawdź ostatni log synchronizacji
            last_log = SyncLog.objects.order_by('-timestamp').first()
            
            is_success = False
            if last_log:
                is_success = last_log.is_success
            
            return JsonResponse({
                'success': True,
                'is_success': is_success,
                'show_sync_status': settings_obj.show_sync_status,
                'show_sync_column': settings_obj.show_sync_column,
                'last_sync_timestamp': last_log.timestamp.isoformat() if last_log else None,
                'retry_interval_minutes': getattr(settings_obj, 'retry_interval_minutes', 15),
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(login_required, name='dispatch')
class AutoLogoutSettingsAPI(View):
    """API endpoint do pobierania ustawień automatycznego wylogowania"""
    
    def get(self, request):
        try:
            settings_obj = SystemSettings.load()
            return JsonResponse({
                'success': True,
                'auto_logout_enabled': settings_obj.auto_logout_enabled,
                'auto_logout_timeout_minutes': settings_obj.auto_logout_timeout_minutes,
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(login_required, name='dispatch')
class SyncPendingRecordsAPI(View):
    """API endpoint do pobierania rekordów w poczekalni (niezsynchronizowanych)"""
    
    def get(self, request):
        try:
            pending_measurements = Pomiar.objects.filter(is_synced=False).order_by('-data_utworzenia')
            pending_defects = Wada.objects.filter(is_synced=False).order_by('-data_utworzenia')
            
            records = []
            for m in pending_measurements:
                try:
                    dt = m.data_utworzenia
                    if dt is None:
                        created_at_str = '—'
                    else:
                        local_dt = timezone.localtime(dt) if getattr(dt, 'tzinfo', None) and dt.tzinfo else dt
                        created_at_str = local_dt.strftime('%Y-%m-%d %H:%M') if hasattr(local_dt, 'strftime') else str(dt)
                    records.append({
                        'id': m.id,
                        'type': 'measurement',
                        'type_display': 'Pomiar',
                        'line': str(m.linia_produkcyjna) if m.linia_produkcyjna else '-',
                        'user': m.uzytkownik.username if m.uzytkownik else '-',
                        'created_at': created_at_str,
                        'details': str(m.rodzaj_testu) if m.rodzaj_testu else '',
                    })
                except Exception:
                    records.append({
                        'id': m.id,
                        'type': 'measurement',
                        'type_display': 'Pomiar',
                        'line': '-',
                        'user': '-',
                        'created_at': '—',
                        'details': '',
                    })
            
            for w in pending_defects:
                try:
                    dt = w.data_utworzenia
                    if dt is None:
                        created_at_str = '—'
                    else:
                        local_dt = timezone.localtime(dt) if getattr(dt, 'tzinfo', None) and dt.tzinfo else dt
                        created_at_str = local_dt.strftime('%Y-%m-%d %H:%M') if hasattr(local_dt, 'strftime') else str(dt)
                    details = (w.opis_wady[:50] + '...') if (w.opis_wady and len(w.opis_wady) > 50) else (w.opis_wady or '')
                    records.append({
                        'id': w.id,
                        'type': 'defect',
                        'type_display': 'Wada',
                        'line': str(w.linia_produkcyjna) if w.linia_produkcyjna else '-',
                        'user': w.uzytkownik.username if w.uzytkownik else '-',
                        'created_at': created_at_str,
                        'details': details,
                    })
                except Exception:
                    records.append({
                        'id': w.id,
                        'type': 'defect',
                        'type_display': 'Wada',
                        'line': '-',
                        'user': '-',
                        'created_at': '—',
                        'details': '',
                    })
            
            # Sortuj po dacie utworzenia (najnowsze pierwsze)
            records.sort(key=lambda x: x['created_at'], reverse=True)
            
            return JsonResponse({
                'success': True,
                'count': len(records),
                'records': records,
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class SyncNowAPI(View):
    """API endpoint do ręcznej synchronizacji rekordów"""
    
    def post(self, request):
        try:
            settings_obj = SystemSettings.load()
            batch_size = settings_obj.retry_batch_size
            
            # Pobierz zaległe rekordy
            pending_measurements = Pomiar.objects.filter(is_synced=False)[:batch_size]
            pending_defects = Wada.objects.filter(is_synced=False)[:batch_size]
            
            synced_count = 0
            failed_count = 0
            errors = []
            
            # Synchronizuj pomiary
            for measurement in pending_measurements:
                if send_to_central_api(measurement):
                    synced_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Pomiar #{measurement.id}")
            
            # Synchronizuj wady
            for defect in pending_defects:
                if send_to_central_api(defect):
                    synced_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Wada #{defect.id}")
            
            return JsonResponse({
                'success': True,
                'synced_count': synced_count,
                'failed_count': failed_count,
                'errors': errors[:10],  # Maksymalnie 10 błędów
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)


@method_decorator(login_required, name='dispatch')
class LineOptionsAPI(View):
    """API zwracające dostępne opcje dla danej linii (na podstawie rejestratora)"""
    
    def get(self, request, line_id):
        try:
            from .models import RejestratorTypKontroli, RejestratorRodzajTestu
            
            linia = LiniaProdukcyjna.objects.select_related('rejestrator').get(id=line_id, aktywna=True)
            rejestrator = linia.rejestrator
            
            # Pobierz opcje na podstawie rejestratora przez modele pośredniczące
            rejestrator_typy = RejestratorTypKontroli.objects.filter(
                rejestrator=rejestrator,
                aktywny=True
            ).select_related('typ_kontroli').order_by('kolejnosc', 'typ_kontroli__nazwa')
            
            if rejestrator_typy.exists():
                typy_kontroli = [rt.typ_kontroli for rt in rejestrator_typy if rt.typ_kontroli.aktywny]
            else:
                typy_kontroli = TypKontroli.objects.filter(aktywny=True).order_by('kolejnosc', 'kod')
            
            rejestrator_rodzaje = RejestratorRodzajTestu.objects.filter(
                rejestrator=rejestrator,
                aktywny=True
            ).select_related('rodzaj_testu').order_by('kolejnosc', 'rodzaj_testu__kod')
            
            if rejestrator_rodzaje.exists():
                rodzaje_testu = [rr.rodzaj_testu for rr in rejestrator_rodzaje if rr.rodzaj_testu.aktywny]
            else:
                rodzaje_testu = RodzajTestu.objects.filter(aktywny=True).order_by('kolejnosc', 'kod')
            
            # Pobierz domyślne wartości z rejestratora
            domyslny_typ_kontroli_id = None
            domyslny_rodzaj_testu_id = None
            
            if rejestrator.domyslny_typ_kontroli:
                domyslny_typ_kontroli_id = rejestrator.domyslny_typ_kontroli.id
            if rejestrator.domyslny_rodzaj_testu:
                domyslny_rodzaj_testu_id = rejestrator.domyslny_rodzaj_testu.id
            
            return JsonResponse({
                'success': True,
                'typy_kontroli': [{'id': t.id, 'kod': t.kod, 'nazwa': t.nazwa} for t in typy_kontroli],
                'rodzaje_testu': [{'id': r.id, 'kod': r.kod, 'nazwa': r.nazwa} for r in rodzaje_testu],
                'domyslny_typ_kontroli_id': domyslny_typ_kontroli_id,
                'domyslny_rodzaj_testu_id': domyslny_rodzaj_testu_id,
            })
        except LiniaProdukcyjna.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Linia nie została znaleziona'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


def custom_404(request, exception):
    """Custom handler dla błędu 404"""
    # Nie przechwytuj żądań do plików statycznych/media - zwróć pustą odpowiedź
    # aby nie pokazywać strony błędu dla brakujących plików statycznych
    if request.path.startswith('/static/') or request.path.startswith('/media/'):
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound()
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    """Custom handler dla błędu 500"""
    return render(request, 'errors/500.html', status=500)
