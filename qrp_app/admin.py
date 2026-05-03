from django.contrib import admin
from django import forms
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.text import slugify
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import Rejestrator, LiniaProdukcyjna, ZmiennaPLC, RFIDCard, Pomiar, Wada, SystemSettings, SyncLog, RodzajTestu, TypKontroli, RejestratorTypKontroli, RejestratorRodzajTestu, AllowedIP
from .settings_import_export import export_settings_to_json, import_settings_from_json
import csv
from io import TextIOWrapper
import re
import json


class RFIDImportForm(forms.Form):
    file = forms.FileField(
        label="Plik (CSV lub XLSX)",
        help_text="Najprościej: eksport z Excela jako CSV UTF-8 z nagłówkami."
    )
    dry_run = forms.BooleanField(
        label="Tryb testowy (nic nie zapisuje)",
        required=False,
        initial=True
    )
    allow_overwrite = forms.BooleanField(
        label="Pozwól nadpisywać konflikty (karta/login)",
        required=False,
        initial=False,
        help_text="Jeśli zaznaczone: w razie konfliktu karta może zostać przepięta na wskazanego użytkownika."
    )


def _normalize_kj(value: str) -> str | None:
    if value is None:
        return None
    v = str(value).strip().upper()
    if not v:
        return None
    if v.startswith("KJ"):
        v = v[2:]
    digits = "".join(ch for ch in v if ch.isdigit())
    if not digits:
        return None
    return "KJ" + digits


def _validate_username_no_polish_chars(username):
    """
    Sprawdza czy username zawiera tylko litery angielskie (a-z) i kropkę.
    Zwraca True jeśli jest poprawny, False jeśli zawiera polskie znaki.
    """
    if not username:
        return False
    # Regex: tylko małe litery angielskie i kropka, format: imie.nazwisko
    pattern = r'^[a-z]+\.[a-z]+$'
    return bool(re.match(pattern, username))


def _normalize_login(login_value: str | None, first_name: str | None, last_name: str | None) -> str | None:
    if login_value:
        return str(login_value).strip().lower()
    if first_name and last_name:
        return f"{str(first_name).strip().lower()}.{str(last_name).strip().lower()}"
    return None


def _split_login_to_names(login_value: str) -> tuple[str, str]:
    parts = login_value.split(".")
    first = parts[0].capitalize() if parts and parts[0] else login_value.capitalize()
    last = parts[1].capitalize() if len(parts) > 1 else ""
    return first, last


def _read_rows_from_upload(uploaded_file):
    """
    Returns list[dict] rows.
    Supported:
    - CSV with header row
    - XLSX (optional, requires openpyxl)
    """
    name = (uploaded_file.name or "").lower()
    if name.endswith(".xlsx"):
        try:
            import openpyxl  # type: ignore
        except Exception:
            raise ValueError("Plik XLSX wymaga biblioteki openpyxl. Zapisz plik w Excelu jako CSV UTF-8 i wgraj ponownie.")
        wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        header = [str(h).strip() if h is not None else "" for h in rows[0]]
        out = []
        for r in rows[1:]:
            d = {}
            for idx, key in enumerate(header):
                if not key:
                    continue
                d[key] = r[idx] if idx < len(r) else None
            if any(v is not None and str(v).strip() for v in d.values()):
                out.append(d)
        return out

    # default CSV
    wrapper = TextIOWrapper(uploaded_file.file, encoding="utf-8-sig", newline="")
    reader = csv.DictReader(wrapper, delimiter=",")
    if reader.fieldnames is None:
        return []
    return [row for row in reader if any((v or "").strip() for v in row.values())]


class ZmiennaPLCInline(admin.TabularInline):
    model = ZmiennaPLC
    extra = 1
    fields = ('nazwa', 'adres_plc', 'typ_danych', 'jednostka', 'wartosc_min', 'wartosc_max', 'aktywna', 'kolejnosc')
    ordering = ('kolejnosc', 'nazwa')
    verbose_name = "Zmienna PLC"
    verbose_name_plural = "Zmienne PLC"
    classes = ('collapse',)


class RejestratorTypKontroliInline(admin.TabularInline):
    model = RejestratorTypKontroli
    extra = 1
    fields = ('typ_kontroli', 'aktywny', 'kolejnosc')
    verbose_name = "Typ kontroli"
    verbose_name_plural = "Dostępne typy kontroli"
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "typ_kontroli":
            kwargs["queryset"] = TypKontroli.objects.filter(aktywny=True).order_by('kolejnosc', 'kod')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class RejestratorRodzajTestuInline(admin.TabularInline):
    model = RejestratorRodzajTestu
    extra = 1
    fields = ('rodzaj_testu', 'aktywny', 'kolejnosc')
    verbose_name = "Rodzaj testu"
    verbose_name_plural = "Dostępne rodzaje testów"
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "rodzaj_testu":
            kwargs["queryset"] = RodzajTestu.objects.filter(aktywny=True).order_by('kolejnosc', 'kod')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class LiniaProdukcyjnaInline(admin.TabularInline):
    model = LiniaProdukcyjna
    extra = 1
    fields = ('nazwa', 'identyfikator_dns', 'url_kamery', 'ip_plc', 'zmienna_numer_zlecenia', 'aktywna')
    verbose_name = "Linia produkcyjna"
    verbose_name_plural = "Linie produkcyjne"
    show_change_link = True


@admin.register(Rejestrator)
class RejestratorAdmin(admin.ModelAdmin):
    change_list_template = "admin/qrp_app/rejestrator/change_list.html"
    list_display = ('nazwa', 'liczba_linii_display', 'aktywny', 'data_utworzenia', 'data_modyfikacji')
    list_filter = ('aktywny', 'data_utworzenia', 'data_modyfikacji')
    search_fields = ('nazwa', 'opis')
    readonly_fields = ('data_utworzenia', 'data_modyfikacji', 'statystyki_display')
    list_per_page = 25
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('nazwa', 'opis', 'aktywny', 'dla_kj')
        }),
        ('Konfiguracja kamery', {
            'fields': ('url_kamery',)
        }),
        ('Domyślne wartości dla formularza', {
            'fields': ('domyslny_typ_kontroli', 'domyslny_rodzaj_testu'),
            'description': 'Ustaw domyślne wartości, które będą automatycznie wybrane po otwarciu strony rejestracji pomiaru. Upewnij się, że wybrane wartości są dostępne dla tego rejestratora w sekcji inline poniżej.'
        }),
        ('Statystyki', {
            'fields': ('statystyki_display',),
            'classes': ('collapse',)
        }),
        ('Daty', {
            'fields': ('data_utworzenia', 'data_modyfikacji'),
            'classes': ('collapse',)
        }),
    )
    inlines = [RejestratorTypKontroliInline, RejestratorRodzajTestuInline, LiniaProdukcyjnaInline]
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "domyslny_typ_kontroli":
            kwargs["queryset"] = TypKontroli.objects.filter(aktywny=True).order_by('kolejnosc', 'kod')
        elif db_field.name == "domyslny_rodzaj_testu":
            kwargs["queryset"] = RodzajTestu.objects.filter(aktywny=True).order_by('kolejnosc', 'kod')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def liczba_linii_display(self, obj):
        count = obj.liczba_linii()
        if count > 0:
            url = '/admin/qrp_app/production-line/' + f'?rejestrator__id__exact={obj.id}'
            return format_html('<a href="{}">{} linii</a>', url, count)
        return '0 linii'
    liczba_linii_display.short_description = "Liczba linii"

    def statystyki_display(self, obj):
        linie = obj.linie_produkcyjne.all()
        linie_aktywne = linie.filter(aktywna=True).count()
        total_zmiennych = sum(linia.liczba_zmiennych() for linia in linie)
        
        html = f"""
        <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
            <p><strong>Liczba linii:</strong> {linie.count()} (aktywnych: {linie_aktywne})</p>
            <p><strong>Łączna liczba zmiennych PLC:</strong> {total_zmiennych}</p>
        </div>
        """
        return mark_safe(html)
    statystyki_display.short_description = "Statystyki"


@admin.register(LiniaProdukcyjna)
class LiniaProdukcyjnaAdmin(admin.ModelAdmin):
    change_list_template = "admin/qrp_app/liniaprodukcyjna/change_list.html"
    list_display = ('nazwa', 'rejestrator', 'identyfikator_dns', 'ip_plc', 'zmienna_numer_zlecenia', 'liczba_zmiennych_display', 'aktywna', 'data_utworzenia')
    list_filter = ('aktywna', 'rejestrator', 'data_utworzenia')
    search_fields = ('nazwa', 'rejestrator__nazwa', 'identyfikator_dns', 'ip_plc', 'url_kamery')
    readonly_fields = ('data_utworzenia', 'data_modyfikacji', 'url_kamery_preview')
    autocomplete_fields = ['rejestrator']
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('rejestrator', 'nazwa', 'opis', 'aktywna')
        }),
        ('Konfiguracja DNS', {
            'fields': ('identyfikator_dns',),
            'description': 'Wprowadź identyfikator linii (np. l9, l2). URL będzie: qrp-{identyfikator}.canpack.ad'
        }),
        ('Konfiguracja kamery', {
            'fields': ('url_kamery', 'url_kamery_preview')
        }),
        ('Konfiguracja PLC', {
            'fields': ('ip_plc', 'zmienna_numer_zlecenia')
        }),
        ('Daty', {
            'fields': ('data_utworzenia', 'data_modyfikacji'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ZmiennaPLCInline]

    def liczba_zmiennych_display(self, obj):
        count = obj.liczba_zmiennych()
        if count > 0:
            url = '/admin/qrp_app/plc-variable/' + f'?linia_produkcyjna__id__exact={obj.id}'
            return format_html('<a href="{}">{} zmiennych</a>', url, count)
        return '0 zmiennych'
    liczba_zmiennych_display.short_description = "Zmienne PLC"

    def url_kamery_preview(self, obj):
        if obj.url_kamery:
            return format_html(
                '<a href="{}" target="_blank" style="color: #007bff;">🔗 Otwórz strumień kamery</a>',
                obj.url_kamery
            )
        return '-'
    url_kamery_preview.short_description = "Podgląd kamery"


@admin.register(ZmiennaPLC)
class ZmiennaPLCAdmin(admin.ModelAdmin):
    change_list_template = "admin/qrp_app/zmiennaplc/change_list.html"
    list_display = ('nazwa', 'linia_produkcyjna', 'adres_plc', 'typ_danych', 'jednostka', 'wartosc_min', 'wartosc_max', 'aktywna', 'kolejnosc')
    list_filter = ('aktywna', 'typ_danych', 'linia_produkcyjna__rejestrator', 'linia_produkcyjna')
    search_fields = ('nazwa', 'adres_plc', 'linia_produkcyjna__nazwa', 'linia_produkcyjna__rejestrator__nazwa')
    readonly_fields = ('data_utworzenia', 'data_modyfikacji')
    autocomplete_fields = ['linia_produkcyjna']
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('linia_produkcyjna', 'nazwa', 'adres_plc', 'typ_danych', 'aktywna', 'kolejnosc')
        }),
        ('Parametry zmiennej', {
            'fields': ('jednostka', 'wartosc_min', 'wartosc_max', 'opis')
        }),
        ('Daty', {
            'fields': ('data_utworzenia', 'data_modyfikacji'),
            'classes': ('collapse',)
        }),
    )
    ordering = ('linia_produkcyjna', 'kolejnosc', 'nazwa')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('linia_produkcyjna', 'linia_produkcyjna__rejestrator')


@admin.register(RFIDCard)
class RFIDCardAdmin(admin.ModelAdmin):
    change_list_template = "admin/qrp_app/rfidcard/change_list.html"
    list_display = ('card_id', 'user', 'numer_kj', 'aktywna', 'data_rejestracji')
    list_filter = ('aktywna', 'data_rejestracji')
    search_fields = ('card_id', 'user__username', 'numer_kj')
    readonly_fields = ('data_rejestracji',)
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('user', 'card_id', 'numer_kj', 'aktywna')
        }),
        ('Daty', {
            'fields': ('data_rejestracji',),
            'classes': ('collapse',)
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_users_view),
                name="qrp_app_rfidcard_import",
            ),
        ]
        return custom + urls

    def import_users_view(self, request):
        """
        Import users + RFID cards from CSV/XLSX.
        Expected columns (recommended):
        - numer_kj (e.g. KJ10 or 10)
        - numer_karty (RFID UID / card_id)
        - login (optional, format: imie.nazwisko) OR imie + nazwisko
        """
        if request.method == "POST":
            form = RFIDImportForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded = form.cleaned_data["file"]
                dry_run = form.cleaned_data["dry_run"]
                allow_overwrite = form.cleaned_data["allow_overwrite"]

                try:
                    rows = _read_rows_from_upload(uploaded)
                except Exception as e:
                    messages.error(request, str(e))
                    return redirect("..")

                created_users = 0
                updated_users = 0
                created_cards = 0
                updated_cards = 0
                skipped = 0
                errors: list[str] = []

                def get_field(row: dict, *keys: str) -> str | None:
                    lowered = {str(k).strip().lower(): k for k in row.keys()}
                    for key in keys:
                        k = key.strip().lower()
                        if k in lowered:
                            val = row.get(lowered[k])
                            return None if val is None else str(val).strip()
                    return None

                for idx, row in enumerate(rows, start=2):  # 1 = header
                    card_id = get_field(row, "numer_karty", "card_id", "rfid", "rfid_code", "karta", "uid")
                    numer_kj = _normalize_kj(get_field(row, "numer_kj", "kj", "kj_number"))
                    login_name = _normalize_login(
                        get_field(row, "login", "username"),
                        get_field(row, "imie", "first_name"),
                        get_field(row, "nazwisko", "last_name"),
                    )

                    if not card_id or not login_name:
                        skipped += 1
                        errors.append(f"Wiersz {idx}: brak wymaganych danych (numer_karty i login/imie+nazwisko).")
                        continue

                    # Walidacja: tylko litery angielskie, bez polskich znaków
                    if not _validate_username_no_polish_chars(login_name):
                        skipped += 1
                        errors.append(
                            f"Wiersz {idx}: login '{login_name}' zawiera polskie znaki. "
                            f"Login może zawierać tylko litery angielskie (a-z) i kropkę. Format: imie.nazwisko"
                        )
                        continue

                    first, last = _split_login_to_names(login_name)

                    # 1) user
                    user = User.objects.filter(username=login_name).first()
                    if user is None:
                        if dry_run:
                            created_users += 1
                        else:
                            user = User.objects.create_user(username=login_name, first_name=first, last_name=last)
                            created_users += 1
                    else:
                        # keep username, update names if missing/different
                        needs_update = (user.first_name != first) or (user.last_name != last)
                        if needs_update:
                            if dry_run:
                                updated_users += 1
                            else:
                                user.first_name = first
                                user.last_name = last
                                user.is_active = True
                                user.save(update_fields=["first_name", "last_name", "is_active"])
                                updated_users += 1

                    if user is None:
                        # dry_run path
                        pass

                    # 2) card mapping
                    existing_card = RFIDCard.objects.filter(card_id=card_id).first()
                    if existing_card and (not user or existing_card.user.username != login_name):
                        if not allow_overwrite:
                            skipped += 1
                            errors.append(
                                f"Wiersz {idx}: karta {card_id} jest już przypisana do {existing_card.user.username} (zaznacz 'Pozwól nadpisywać konflikty')."
                            )
                            continue

                    if user and hasattr(user, "rfid_card") and user.rfid_card.card_id != card_id:
                        if not allow_overwrite:
                            skipped += 1
                            errors.append(
                                f"Wiersz {idx}: użytkownik {login_name} ma już inną kartę ({user.rfid_card.card_id})."
                            )
                            continue

                    if dry_run:
                        if existing_card:
                            updated_cards += 1
                        else:
                            created_cards += 1
                        continue

                    # apply changes
                    if existing_card:
                        existing_card.user = user
                        existing_card.numer_kj = numer_kj
                        existing_card.aktywna = True
                        existing_card.save(update_fields=["user", "numer_kj", "aktywna"])
                        updated_cards += 1
                    else:
                        RFIDCard.objects.create(user=user, card_id=card_id, numer_kj=numer_kj, aktywna=True)
                        created_cards += 1

                context = dict(
                    self.admin_site.each_context(request),
                    title="Import użytkowników (RFID)",
                    form=form,
                    dry_run=dry_run,
                    results={
                        "created_users": created_users,
                        "updated_users": updated_users,
                        "created_cards": created_cards,
                        "updated_cards": updated_cards,
                        "skipped": skipped,
                        "errors": errors[:200],
                    },
                    required_columns=[
                        "numer_karty (wymagane)",
                        "login (wymagane jeśli brak imie+nazwisko) — format: imie.nazwisko",
                        "imie + nazwisko (alternatywa dla login)",
                        "numer_kj (opcjonalnie) — np. KJ10 lub 10",
                    ],
                )
                return render(request, "admin/qrp_app/rfidcard/import_users.html", context)
        else:
            form = RFIDImportForm()

        context = dict(
            self.admin_site.each_context(request),
            title="Import użytkowników (RFID)",
            form=form,
            required_columns=[
                "numer_karty (wymagane)",
                "login (wymagane jeśli brak imie+nazwisko) — format: imie.nazwisko",
                "imie + nazwisko (alternatywa dla login)",
                "numer_kj (opcjonalnie) — np. KJ10 lub 10",
            ],
        )
        return render(request, "admin/qrp_app/rfidcard/import_users.html", context)


@admin.register(Pomiar)
class PomiarAdmin(admin.ModelAdmin):
    list_display = ('id', 'linia_produkcyjna', 'uzytkownik', 'typ_kontroli', 'rodzaj_testu', 'is_synced', 'data_utworzenia')
    list_filter = ('typ_kontroli', 'rodzaj_testu', 'data_utworzenia', 'linia_produkcyjna', 'is_synced')
    search_fields = ('numer_zlecenia', 'komentarz', 'uzytkownik__username', 'linia_produkcyjna__nazwa')
    readonly_fields = ('data_utworzenia', 'is_synced', 'synced_at')
    date_hierarchy = 'data_utworzenia'
    actions = ['mark_as_synced']
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('linia_produkcyjna', 'uzytkownik', 'typ_kontroli', 'rodzaj_testu', 'numer_zlecenia')
        }),
        ('Szczegóły', {
            'fields': ('komentarz', 'zdjecie')
        }),
        ('Synchronizacja', {
            'fields': ('is_synced', 'synced_at'),
            'classes': ('collapse',)
        }),
        ('Daty', {
            'fields': ('data_utworzenia',),
            'classes': ('collapse',)
        }),
    )

    @admin.action(description='Oznacz jako zsynchronizowane')
    def mark_as_synced(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(is_synced=False).update(is_synced=True, synced_at=timezone.now())
        self.message_user(request, f'Oznaczono {updated} pomiarów jako zsynchronizowane.')


@admin.register(Wada)
class WadaAdmin(admin.ModelAdmin):
    list_display = ('id', 'linia_produkcyjna', 'uzytkownik', 'typ_kontroli', 'opis_wady_short', 'is_synced', 'data_utworzenia')
    list_filter = ('typ_kontroli', 'data_utworzenia', 'linia_produkcyjna', 'is_synced')
    search_fields = ('opis_wady', 'komentarz', 'numer_zlecenia', 'uzytkownik__username', 'linia_produkcyjna__nazwa')
    readonly_fields = ('data_utworzenia', 'is_synced', 'synced_at')
    date_hierarchy = 'data_utworzenia'
    actions = ['mark_as_synced']
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('linia_produkcyjna', 'uzytkownik', 'typ_kontroli', 'numer_zlecenia')
        }),
        ('Opis wady', {
            'fields': ('opis_wady', 'komentarz', 'zdjecie')
        }),
        ('Synchronizacja', {
            'fields': ('is_synced', 'synced_at'),
            'classes': ('collapse',)
        }),
        ('Daty', {
            'fields': ('data_utworzenia',),
            'classes': ('collapse',)
        }),
    )

    def opis_wady_short(self, obj):
        return obj.opis_wady[:50] + '...' if len(obj.opis_wady) > 50 else obj.opis_wady
    opis_wady_short.short_description = 'Opis wady'

    @admin.action(description='Oznacz jako zsynchronizowane')
    def mark_as_synced(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(is_synced=False).update(is_synced=True, synced_at=timezone.now())
        self.message_user(request, f'Oznaczono {updated} wad jako zsynchronizowane.')


class SettingsImportForm(forms.Form):
    file = forms.FileField(
        label="Plik JSON z ustawieniami",
        help_text="Wybierz plik JSON wyeksportowany wcześniej z systemu"
    )
    dry_run = forms.BooleanField(
        label="Tryb testowy (nic nie zapisuje)",
        required=False,
        initial=True,
        help_text="Zaznacz, aby tylko sprawdzić poprawność danych bez zapisywania"
    )
    overwrite_mode = forms.BooleanField(
        label="Tryb nadpisywania (usuń istniejące i zaimportuj z pliku)",
        required=False,
        initial=False,
        help_text="Jeśli zaznaczone: wszystkie istniejące dane (oprócz ustawień systemowych) zostaną usunięte i zastąpione danymi z pliku. Jeśli odznaczone: dane z pliku będą dopisane/aktualizowane do istniejących."
    )


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """Admin dla ustawień systemowych (singleton)"""
    
    def has_add_permission(self, request):
        # Tylko jedna instancja - blokuj dodawanie
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Nie pozwól usuwać - zawsze musi być jedna instancja
        return False
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-settings/', self.admin_site.admin_view(self.export_settings), name='qrp_app_systemsettings_export'),
            path('import-settings/', self.admin_site.admin_view(self.import_settings), name='qrp_app_systemsettings_import'),
        ]
        return custom_urls + urls
    
    def export_settings(self, request):
        """Eksportuje wszystkie ustawienia do pliku JSON"""
        try:
            data = export_settings_to_json()
            data['export_date'] = timezone.now().isoformat()
            
            response = HttpResponse(
                json.dumps(data, indent=2, ensure_ascii=False),
                content_type='application/json; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="qrp_settings_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
            return response
        except Exception as e:
            messages.error(request, f"Błąd podczas eksportu ustawień: {str(e)}")
            return redirect(reverse('admin:qrp_app_systemsettings_changelist'))
    
    def import_settings(self, request):
        """Importuje ustawienia z pliku JSON"""
        if request.method == 'POST':
            form = SettingsImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                dry_run = form.cleaned_data.get('dry_run', False)
                overwrite_mode = form.cleaned_data.get('overwrite_mode', False)
                
                try:
                    # Odczytaj plik JSON
                    content = file.read().decode('utf-8')
                    json_data = json.loads(content)
                    
                    # Importuj ustawienia
                    results = import_settings_from_json(json_data, dry_run=dry_run, overwrite_mode=overwrite_mode)
                    
                    if dry_run:
                        # Tryb testowy - pokaż podsumowanie
                        context = dict(
                            self.admin_site.each_context(request),
                            title="Import ustawień - tryb testowy",
                            form=form,
                            results=results,
                            dry_run=True,
                        )
                        return render(request, 'admin/qrp_app/systemsettings/import_results.html', context)
                    else:
                        # Rzeczywisty import
                        if results['success']:
                            msg = f"Import zakończony pomyślnie! Utworzono: {results['created']}, zaktualizowano: {results['updated']}"
                            if results.get('deleted', 0) > 0:
                                msg += f", usunięto: {results['deleted']} (tryb nadpisywania)"
                            messages.success(request, msg)
                            if results['warnings']:
                                for warning in results['warnings'][:10]:  # Pokaż max 10 ostrzeżeń
                                    messages.warning(request, warning)
                        else:
                            messages.error(request, f"Import zakończony z błędami. Utworzono: {results['created']}, zaktualizowano: {results['updated']}")
                            for error in results['errors'][:10]:  # Pokaż max 10 błędów
                                messages.error(request, error)
                        
                        return redirect(reverse('admin:qrp_app_systemsettings_changelist'))
                except json.JSONDecodeError as e:
                    messages.error(request, f"Nieprawidłowy format pliku JSON: {str(e)}")
                except Exception as e:
                    messages.error(request, f"Błąd podczas importu ustawień: {str(e)}")
        else:
            form = SettingsImportForm()
        
        context = dict(
            self.admin_site.each_context(request),
            title="Import ustawień",
            form=form,
        )
        return render(request, 'admin/qrp_app/systemsettings/import_settings.html', context)
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_export_import'] = True
        return super().changelist_view(request, extra_context)
    
    fieldsets = (
        ('API Centralne', {
            'fields': ('api_url', 'api_token'),
            'description': 'Konfiguracja połączenia z centralnym API'
        }),
        ('Retencja danych', {
            'fields': ('log_retention_days', 'data_retention_days'),
            'description': 'Okres przechowywania logów i danych przed usunięciem'
        }),
        ('Automatyczna synchronizacja', {
            'fields': ('retry_interval_minutes', 'retry_batch_size'),
            'description': 'Ustawienia automatycznej synchronizacji zaległych rekordów'
        }),
        ('Widoczność', {
            'fields': ('show_sync_status', 'show_sync_column'),
            'description': 'Ustawienia wyświetlania statusu synchronizacji w interfejsie'
        }),
        ('Eksport CSV', {
            'fields': ('csv_export_enabled', 'csv_output_path', 'csv_line_mapping', 'csv_machine_mapping', 'csv_inspection_mapping'),
            'description': 'Ustawienia eksportu CSV dla pomiarów. Format JSON dla mapowań: {"Klucz": "Wartość"}. Przykład mapowania linii: {"Linia 2": "C020", "Linia 3": "C030"}'
        }),
        ('Automatyczne wylogowanie', {
            'fields': ('auto_logout_enabled', 'auto_logout_timeout_minutes'),
            'description': 'Ustawienia automatycznego wylogowania użytkownika po okresie bezczynności'
        }),
        ('Informacje', {
            'fields': ('data_modyfikacji',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('data_modyfikacji',)


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'status_display', 'record_type', 'record_id', 'message_short', 'timestamp', 'is_success')
    list_filter = ('is_success', 'record_type', 'timestamp')
    search_fields = ('message', 'record_id')
    readonly_fields = ('status_code', 'message', 'timestamp', 'is_success', 'record_type', 'record_id')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    
    def status_display(self, obj):
        if obj.is_success:
            return mark_safe('<span style="color: green;">✓</span>')
        return mark_safe('<span style="color: red;">✗</span>')
    status_display.short_description = 'Status'
    
    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Komunikat'
    
    def has_add_permission(self, request):
        # Logi są tworzone automatycznie przez system
        return False


@admin.register(RodzajTestu)
class RodzajTestuAdmin(admin.ModelAdmin):
    list_display = ('kod', 'nazwa', 'aktywny', 'kolejnosc', 'data_utworzenia')
    list_filter = ('aktywny', 'data_utworzenia')
    search_fields = ('kod', 'nazwa')
    ordering = ('kolejnosc', 'kod')
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('kod', 'nazwa', 'aktywny', 'kolejnosc')
        }),
        ('Daty', {
            'fields': ('data_utworzenia', 'data_modyfikacji'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('data_utworzenia', 'data_modyfikacji')


@admin.register(TypKontroli)
class TypKontroliAdmin(admin.ModelAdmin):
    change_list_template = "admin/qrp_app/typkontroli/change_list.html"
    list_display = ('kod', 'nazwa', 'aktywny', 'kolejnosc', 'data_utworzenia')
    list_filter = ('aktywny', 'data_utworzenia')
    search_fields = ('kod', 'nazwa')
    ordering = ('kolejnosc', 'kod')
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('kod', 'nazwa', 'aktywny', 'kolejnosc')
        }),
        ('Daty', {
            'fields': ('data_utworzenia', 'data_modyfikacji'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('data_utworzenia', 'data_modyfikacji')


@admin.register(AllowedIP)
class AllowedIPAdmin(admin.ModelAdmin):
    change_list_template = "admin/qrp_app/allowedip/change_list.html"
    list_display = ('ip_address', 'opis', 'aktywny', 'data_utworzenia', 'data_modyfikacji')
    list_filter = ('aktywny', 'data_utworzenia')
    search_fields = ('ip_address', 'opis')
    ordering = ('ip_address',)
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('ip_address', 'opis', 'aktywny')
        }),
        ('Daty', {
            'fields': ('data_utworzenia', 'data_modyfikacji'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('data_utworzenia', 'data_modyfikacji')
    
    def get_queryset(self, request):
        """Optymalizacja zapytań"""
        return super().get_queryset(request).select_related()


admin.site.site_header = "QRP Control System - Panel Administracyjny"
admin.site.site_title = "QRP Admin"
admin.site.index_title = "Witaj w panelu administracyjnym QRP"
