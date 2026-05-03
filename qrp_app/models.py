from django.db import models
from django.core.validators import URLValidator, validate_ipv4_address
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


class Rejestrator(models.Model):
    nazwa = models.CharField(
        max_length=200,
        verbose_name="Nazwa rejestratora",
        help_text="Unikalna nazwa identyfikująca rejestrator"
    )
    url_kamery = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="URL kamery",
        help_text="Adres URL strumienia kamery (np. http://192.168.1.100:8080/stream)",
        validators=[URLValidator()]
    )
    opis = models.TextField(
        blank=True,
        null=True,
        verbose_name="Opis",
        help_text="Dodatkowy opis rejestratora"
    )
    aktywny = models.BooleanField(
        default=True,
        verbose_name="Aktywny",
        help_text="Czy rejestrator jest aktywny w systemie"
    )
    dostepne_typy_kontroli = models.ManyToManyField(
        'TypKontroli',
        blank=True,
        through='RejestratorTypKontroli',
        related_name='rejestratory',
        verbose_name="Dostępne typy kontroli",
        help_text="Wybierz typy kontroli dostępne dla tego rejestratora. Jeśli puste, dostępne są wszystkie aktywne typy."
    )
    dostepne_rodzaje_testu = models.ManyToManyField(
        'RodzajTestu',
        blank=True,
        through='RejestratorRodzajTestu',
        related_name='rejestratory',
        verbose_name="Dostępne rodzaje testów",
        help_text="Wybierz rodzaje testów dostępne dla tego rejestratora. Jeśli puste, dostępne są wszystkie aktywne rodzaje."
    )
    domyslny_typ_kontroli = models.ForeignKey(
        'TypKontroli',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejestratory_domyslne_typ',
        verbose_name="Domyślny typ kontroli",
        help_text="Typ kontroli, który będzie automatycznie wybrany po otwarciu strony rejestracji pomiaru"
    )
    domyslny_rodzaj_testu = models.ForeignKey(
        'RodzajTestu',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejestratory_domyslne_rodzaj',
        verbose_name="Domyślny rodzaj testu",
        help_text="Rodzaj testu, który będzie automatycznie wybrany po otwarciu strony rejestracji pomiaru"
    )
    dla_kj = models.BooleanField(
        default=True,
        verbose_name="Dla KJ",
        help_text="Czy rejestrator jest przeznaczony dla KJ. Jeśli odznaczone, logowanie wymaga tylko imie.nazwisko bez numeru KJ"
    )
    data_utworzenia = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )
    data_modyfikacji = models.DateTimeField(
        auto_now=True,
        verbose_name="Data modyfikacji"
    )

    class Meta:
        verbose_name = "Rejestrator"
        verbose_name_plural = "Rejestratory"
        ordering = ['nazwa']
        indexes = [
            models.Index(fields=['nazwa']),
            models.Index(fields=['aktywny']),
        ]

    def __str__(self):
        return self.nazwa

    def liczba_linii(self):
        return self.linie_produkcyjne.count()
    liczba_linii.short_description = "Liczba linii"


class LiniaProdukcyjna(models.Model):
    rejestrator = models.ForeignKey(
        Rejestrator,
        on_delete=models.CASCADE,
        related_name='linie_produkcyjne',
        verbose_name="Rejestrator",
        help_text="Rejestrator, do którego przypisana jest linia"
    )
    nazwa = models.CharField(
        max_length=200,
        verbose_name="Nazwa linii",
        help_text="Nazwa identyfikująca linię produkcyjną"
    )
    url_kamery = models.URLField(
        max_length=500,
        verbose_name="URL kamery",
        help_text="Adres URL strumienia kamery (np. http://192.168.1.100:8080/stream)",
        validators=[URLValidator()]
    )
    ip_plc = models.GenericIPAddressField(
        protocol='IPv4',
        verbose_name="IP PLC",
        help_text="Adres IP sterownika PLC Allen Bradley (np. 10.11.x.x)"
    )
    zmienna_numer_zlecenia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Zmienna PLC - Numer zlecenia",
        help_text="Nazwa zmiennej PLC dla numeru zlecenia (np. Qrp_Order_L9)"
    )
    identyfikator_dns = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Identyfikator DNS",
        help_text="Identyfikator używany w URL DNS (np. l9, l2). URL będzie: qrp-{identyfikator}.canpack.ad. Wiele linii może mieć ten sam identyfikator."
    )
    aktywna = models.BooleanField(
        default=True,
        verbose_name="Aktywna",
        help_text="Czy linia jest aktywna"
    )
    opis = models.TextField(
        blank=True,
        null=True,
        verbose_name="Opis",
        help_text="Dodatkowy opis linii produkcyjnej"
    )
    data_utworzenia = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )
    data_modyfikacji = models.DateTimeField(
        auto_now=True,
        verbose_name="Data modyfikacji"
    )

    class Meta:
        verbose_name = "Linia produkcyjna"
        verbose_name_plural = "Linie produkcyjne"
        ordering = ['rejestrator', 'nazwa']
        unique_together = [['rejestrator', 'nazwa']]
        indexes = [
            models.Index(fields=['rejestrator', 'aktywna']),
            models.Index(fields=['ip_plc']),
        ]

    def __str__(self):
        return f"{self.rejestrator.nazwa} - {self.nazwa}"

    def liczba_zmiennych(self):
        return self.zmienne_plc.count()
    liczba_zmiennych.short_description = "Liczba zmiennych"


class ZmiennaPLC(models.Model):
    TYPY_DANYCH = [
        ('BOOL', 'BOOL - Wartość logiczna'),
        ('INT', 'INT - Liczba całkowita 16-bit'),
        ('DINT', 'DINT - Liczba całkowita 32-bit'),
        ('REAL', 'REAL - Liczba zmiennoprzecinkowa'),
        ('STRING', 'STRING - Ciąg znaków'),
    ]

    linia_produkcyjna = models.ForeignKey(
        LiniaProdukcyjna,
        on_delete=models.CASCADE,
        related_name='zmienne_plc',
        verbose_name="Linia produkcyjna",
        help_text="Linia produkcyjna, do której przypisana jest zmienna"
    )
    nazwa = models.CharField(
        max_length=200,
        verbose_name="Nazwa zmiennej",
        help_text="Nazwa identyfikująca zmienną (np. 'Temperatura', 'Cisnienie')"
    )
    adres_plc = models.CharField(
        max_length=50,
        verbose_name="Adres PLC",
        help_text="Adres zmiennej w PLC (np. 'DB1.DBD0', 'MW100', 'I0.0')"
    )
    typ_danych = models.CharField(
        max_length=10,
        choices=TYPY_DANYCH,
        default='REAL',
        verbose_name="Typ danych",
        help_text="Typ danych zmiennej w PLC"
    )
    jednostka = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Jednostka",
        help_text="Jednostka miary (np. '°C', 'bar', 'm/s')"
    )
    wartosc_min = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Wartość minimalna",
        help_text="Minimalna wartość zmiennej (opcjonalnie)"
    )
    wartosc_max = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Wartość maksymalna",
        help_text="Maksymalna wartość zmiennej (opcjonalnie)"
    )
    opis = models.TextField(
        blank=True,
        null=True,
        verbose_name="Opis",
        help_text="Dodatkowy opis zmiennej"
    )
    aktywna = models.BooleanField(
        default=True,
        verbose_name="Aktywna",
        help_text="Czy zmienna jest aktywna i czytana z PLC"
    )
    kolejnosc = models.PositiveIntegerField(
        default=0,
        verbose_name="Kolejność",
        help_text="Kolejność wyświetlania zmiennej (mniejsza wartość = wyżej)"
    )
    data_utworzenia = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )
    data_modyfikacji = models.DateTimeField(
        auto_now=True,
        verbose_name="Data modyfikacji"
    )

    class Meta:
        verbose_name = "Zmienna PLC"
        verbose_name_plural = "Zmienne PLC"
        ordering = ['linia_produkcyjna', 'kolejnosc', 'nazwa']
        unique_together = [['linia_produkcyjna', 'adres_plc']]
        indexes = [
            models.Index(fields=['linia_produkcyjna', 'aktywna']),
            models.Index(fields=['kolejnosc']),
        ]

    def __str__(self):
        jednostka_str = f" [{self.jednostka}]" if self.jednostka else ""
        return f"{self.linia_produkcyjna.nazwa} - {self.nazwa}{jednostka_str}"

    def clean(self):
        if self.wartosc_min is not None and self.wartosc_max is not None:
            if self.wartosc_min >= self.wartosc_max:
                raise ValidationError({
                    'wartosc_max': _('Wartość maksymalna musi być większa od minimalnej.')
                })


class RFIDCard(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='rfid_card',
        verbose_name="Użytkownik",
        help_text="Użytkownik przypisany do karty RFID"
    )
    card_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="ID karty RFID",
        help_text="Unikalny identyfikator karty RFID"
    )
    numer_kj = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Numer KJ",
        help_text="Numer KJ użytkownika"
    )
    data_rejestracji = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data rejestracji"
    )
    aktywna = models.BooleanField(
        default=True,
        verbose_name="Aktywna",
        help_text="Czy karta jest aktywna"
    )

    class Meta:
        verbose_name = "Karta RFID"
        verbose_name_plural = "Karty RFID"
        ordering = ['-data_rejestracji']
        indexes = [
            models.Index(fields=['card_id']),
            models.Index(fields=['aktywna']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.card_id}"


class Pomiar(models.Model):
    linia_produkcyjna = models.ForeignKey(
        LiniaProdukcyjna,
        on_delete=models.CASCADE,
        related_name='pomiary',
        verbose_name="Linia produkcyjna"
    )
    uzytkownik = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pomiary',
        verbose_name="Użytkownik"
    )
    typ_kontroli = models.ForeignKey(
        'TypKontroli',
        on_delete=models.PROTECT,
        related_name='pomiary',
        verbose_name="Typ kontroli"
    )
    rodzaj_testu = models.ForeignKey(
        'RodzajTestu',
        on_delete=models.PROTECT,
        related_name='pomiary',
        verbose_name="Rodzaj testu"
    )
    numer_zlecenia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Numer zlecenia"
    )
    komentarz = models.TextField(
        blank=True,
        null=True,
        verbose_name="Komentarz"
    )
    zdjecie = models.ImageField(
        upload_to='pomiary/',
        blank=True,
        null=True,
        verbose_name="Zdjęcie"
    )
    is_synced = models.BooleanField(
        default=False,
        verbose_name="Zsynchronizowano",
        help_text="Czy rekord został zsynchronizowany z centralnym API"
    )
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data synchronizacji",
        help_text="Data i czas ostatniej synchronizacji z centralnym API"
    )
    data_utworzenia = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )

    class Meta:
        verbose_name = "Pomiar"
        verbose_name_plural = "Pomiary"
        ordering = ['-data_utworzenia']
        indexes = [
            models.Index(fields=['-data_utworzenia']),
            models.Index(fields=['linia_produkcyjna', '-data_utworzenia']),
            models.Index(fields=['uzytkownik', '-data_utworzenia']),
        ]

    def get_rodzaj_testu_display(self):
        """Metoda pomocnicza dla kompatybilności z poprzednim kodem"""
        if self.rodzaj_testu:
            return str(self.rodzaj_testu)
        return ""
    
    def __str__(self):
        rodzaj_display = self.get_rodzaj_testu_display()
        return f"Pomiar #{self.id} - {self.linia_produkcyjna} - {rodzaj_display}"


class Wada(models.Model):
    linia_produkcyjna = models.ForeignKey(
        LiniaProdukcyjna,
        on_delete=models.CASCADE,
        related_name='wady',
        verbose_name="Linia produkcyjna"
    )
    uzytkownik = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='wady',
        verbose_name="Użytkownik"
    )
    typ_kontroli = models.ForeignKey(
        'TypKontroli',
        on_delete=models.PROTECT,
        related_name='wady',
        verbose_name="Typ kontroli"
    )
    opis_wady = models.TextField(
        verbose_name="Opis wady",
        help_text="Szczegółowy opis zaobserwowanej wady"
    )
    komentarz = models.TextField(
        blank=True,
        null=True,
        verbose_name="Dodatkowe uwagi"
    )
    numer_zlecenia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Numer zlecenia"
    )
    zdjecie = models.ImageField(
        upload_to='wady/',
        blank=True,
        null=True,
        verbose_name="Zdjęcie"
    )
    is_synced = models.BooleanField(
        default=False,
        verbose_name="Zsynchronizowano",
        help_text="Czy rekord został zsynchronizowany z centralnym API"
    )
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data synchronizacji",
        help_text="Data i czas ostatniej synchronizacji z centralnym API"
    )
    data_utworzenia = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )

    class Meta:
        verbose_name = "Wada"
        verbose_name_plural = "Wady"
        ordering = ['-data_utworzenia']
        indexes = [
            models.Index(fields=['-data_utworzenia']),
            models.Index(fields=['linia_produkcyjna', '-data_utworzenia']),
            models.Index(fields=['uzytkownik', '-data_utworzenia']),
            models.Index(fields=['is_synced']),
        ]

    def __str__(self):
        return f"Wada #{self.id} - {self.linia_produkcyjna} - {self.opis_wady[:50]}"


class SystemSettings(models.Model):
    """
    Singleton model dla ustawień systemowych synchronizacji.
    W panelu admin zawsze będzie tylko jedna instancja.
    """
    api_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="URL API centralnego",
        help_text="Adres URL centralnego API do synchronizacji danych"
    )
    api_token = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Token API",
        help_text="Token autoryzacyjny do komunikacji z centralnym API",
    )
    log_retention_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Retencja logów (dni)",
        help_text="Liczba dni przechowywania logów synchronizacji"
    )
    data_retention_days = models.PositiveIntegerField(
        default=90,
        verbose_name="Retencja danych (dni)",
        help_text="Liczba dni przechowywania zsynchronizowanych rekordów przed usunięciem"
    )
    retry_interval_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name="Interwał ponawiania (minuty)",
        help_text="Częstotliwość automatycznych prób synchronizacji zaległych rekordów"
    )
    retry_batch_size = models.PositiveIntegerField(
        default=10,
        verbose_name="Rozmiar paczki",
        help_text="Liczba rekordów wysyłanych w jednej paczce podczas synchronizacji"
    )
    show_sync_status = models.BooleanField(
        default=True,
        verbose_name="Pokaż status synchronizacji",
        help_text="Czy wyświetlać status synchronizacji użytkownikom"
    )
    show_sync_column = models.BooleanField(
        default=True,
        verbose_name="Pokaż kolumnę 'Wysłano'",
        help_text="Czy wyświetlać kolumnę 'Wysłano' w tabeli archiwum"
    )
    csv_export_enabled = models.BooleanField(
        default=True,
        verbose_name="Eksport CSV włączony",
        help_text="Czy automatycznie generować pliki CSV dla pomiarów"
    )
    csv_output_path = models.CharField(
        max_length=500,
        default='C:/QRP_Exports/',
        verbose_name="Ścieżka eksportu CSV",
        help_text="Ścieżka do folderu, gdzie będą zapisywane pliki CSV (np. C:/QRP_Exports/)"
    )
    csv_line_mapping = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Mapowanie linii (kod)",
        help_text="Mapowanie nazw linii na kody (JSON), np. {'Linia 2': 'C020', 'Linia 3': 'C030'}"
    )
    csv_machine_mapping = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Mapowanie linii (maszyna)",
        help_text="Mapowanie nazw linii na nazwy maszyn (JSON), np. {'Linia 2': 'L020_PAL_01', 'Linia 3': 'L030_PAL_01'}"
    )
    csv_inspection_mapping = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Mapowanie rodzajów testów",
        help_text="Mapowanie kodów rodzajów testów na nazwy (JSON), np. {'1': 'Pokrycie lakierem...', '2': 'Pokrycie denka...'}"
    )
    auto_logout_enabled = models.BooleanField(
        default=True,
        verbose_name="Automatyczne wylogowanie włączone",
        help_text="Czy automatycznie wylogowywać użytkownika po okresie bezczynności"
    )
    auto_logout_timeout_minutes = models.PositiveIntegerField(
        default=5,
        verbose_name="Czas bezczynności przed wylogowaniem (minuty)",
        help_text="Liczba minut bezczynności po których użytkownik zostanie automatycznie wylogowany"
    )
    data_modyfikacji = models.DateTimeField(
        auto_now=True,
        verbose_name="Data modyfikacji"
    )

    class Meta:
        verbose_name = "Ustawienia systemowe"
        verbose_name_plural = "Ustawienia systemowe"
        ordering = ['-data_modyfikacji']

    def __str__(self):
        return "Ustawienia synchronizacji"

    def save(self, *args, **kwargs):
        """Zapewnia, że zawsze istnieje tylko jedna instancja (singleton)"""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Zabezpiecza przed usunięciem jedynej instancji"""
        pass

    @classmethod
    def load(cls):
        """Zwraca istniejącą instancję lub tworzy nową z wartościami domyślnymi"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class RodzajTestu(models.Model):
    """Model do zarządzania opcjami rodzaju testu w panelu admin"""
    kod = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Kod",
        help_text="Unikalny kod identyfikujący rodzaj testu (np. '1', '2', 'test_custom')"
    )
    nazwa = models.CharField(
        max_length=500,
        verbose_name="Nazwa",
        help_text="Pełna nazwa rodzaju testu wyświetlana użytkownikowi"
    )
    aktywny = models.BooleanField(
        default=True,
        verbose_name="Aktywny",
        help_text="Czy ta opcja jest dostępna w formularzu rejestracji"
    )
    kolejnosc = models.PositiveIntegerField(
        default=0,
        verbose_name="Kolejność",
        help_text="Kolejność wyświetlania (mniejsza wartość = wyżej)"
    )
    data_utworzenia = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )
    data_modyfikacji = models.DateTimeField(
        auto_now=True,
        verbose_name="Data modyfikacji"
    )

    class Meta:
        verbose_name = "Rodzaj testu"
        verbose_name_plural = "Rodzaje testów"
        ordering = ['kolejnosc', 'kod']
        indexes = [
            models.Index(fields=['aktywny']),
            models.Index(fields=['kolejnosc']),
        ]

    def __str__(self):
        return f"{self.kod}. {self.nazwa}"


class TypKontroli(models.Model):
    """Model do zarządzania opcjami typu kontroli w panelu admin"""
    kod = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Kod",
        help_text="Unikalny kod identyfikujący typ kontroli (np. 'Standardowe', 'Ponowna kontrola')"
    )
    nazwa = models.CharField(
        max_length=100,
        verbose_name="Nazwa",
        help_text="Nazwa typu kontroli wyświetlana użytkownikowi"
    )
    aktywny = models.BooleanField(
        default=True,
        verbose_name="Aktywny",
        help_text="Czy ta opcja jest dostępna w formularzu rejestracji"
    )
    kolejnosc = models.PositiveIntegerField(
        default=0,
        verbose_name="Kolejność",
        help_text="Kolejność wyświetlania (mniejsza wartość = wyżej)"
    )
    data_utworzenia = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )
    data_modyfikacji = models.DateTimeField(
        auto_now=True,
        verbose_name="Data modyfikacji"
    )

    class Meta:
        verbose_name = "Typ kontroli"
        verbose_name_plural = "Typy kontroli"
        ordering = ['kolejnosc', 'kod']
        indexes = [
            models.Index(fields=['aktywny']),
            models.Index(fields=['kolejnosc']),
        ]

    def __str__(self):
        return self.nazwa


class RejestratorTypKontroli(models.Model):
    """Model pośredniczący dla relacji ManyToMany między Rejestrator a TypKontroli"""
    rejestrator = models.ForeignKey(
        Rejestrator,
        on_delete=models.CASCADE,
        verbose_name="Rejestrator"
    )
    typ_kontroli = models.ForeignKey(
        TypKontroli,
        on_delete=models.CASCADE,
        verbose_name="Typ kontroli"
    )
    aktywny = models.BooleanField(
        default=True,
        verbose_name="Aktywny",
        help_text="Czy ten typ kontroli jest dostępny dla tego rejestratora"
    )
    kolejnosc = models.PositiveIntegerField(
        default=0,
        verbose_name="Kolejność",
        help_text="Kolejność wyświetlania w formularzu"
    )
    data_dodania = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data dodania"
    )

    class Meta:
        verbose_name = "Typ kontroli rejestratora"
        verbose_name_plural = "Typy kontroli rejestratorów"
        unique_together = ('rejestrator', 'typ_kontroli')
        ordering = ('kolejnosc', 'typ_kontroli__nazwa')

    def __str__(self):
        return f"{self.rejestrator.nazwa} - {self.typ_kontroli.nazwa}"


class RejestratorRodzajTestu(models.Model):
    """Model pośredniczący dla relacji ManyToMany między Rejestrator a RodzajTestu"""
    rejestrator = models.ForeignKey(
        Rejestrator,
        on_delete=models.CASCADE,
        verbose_name="Rejestrator"
    )
    rodzaj_testu = models.ForeignKey(
        RodzajTestu,
        on_delete=models.CASCADE,
        verbose_name="Rodzaj testu"
    )
    aktywny = models.BooleanField(
        default=True,
        verbose_name="Aktywny",
        help_text="Czy ten rodzaj testu jest dostępny dla tego rejestratora"
    )
    kolejnosc = models.PositiveIntegerField(
        default=0,
        verbose_name="Kolejność",
        help_text="Kolejność wyświetlania w formularzu"
    )
    data_dodania = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data dodania"
    )

    class Meta:
        verbose_name = "Rodzaj testu rejestratora"
        verbose_name_plural = "Rodzaje testów rejestratorów"
        unique_together = ('rejestrator', 'rodzaj_testu')
        ordering = ('kolejnosc', 'rodzaj_testu__kod')

    def __str__(self):
        return f"{self.rejestrator.nazwa} - {self.rodzaj_testu.nazwa}"


class SyncLog(models.Model):
    """Log synchronizacji z centralnym API"""
    status_code = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Kod statusu HTTP"
    )
    message = models.TextField(
        verbose_name="Komunikat"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data i czas"
    )
    is_success = models.BooleanField(
        default=False,
        verbose_name="Sukces",
        help_text="Czy synchronizacja zakończyła się sukcesem"
    )
    record_type = models.CharField(
        max_length=20,
        choices=[
            ('measurement', 'Pomiar'),
            ('defect', 'Wada'),
        ],
        null=True,
        blank=True,
        verbose_name="Typ rekordu"
    )
    record_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="ID rekordu"
    )

    class Meta:
        verbose_name = "Log synchronizacji"
        verbose_name_plural = "Logi synchronizacji"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['is_success']),
        ]

    def __str__(self):
        status = "✓" if self.is_success else "✗"
        return f"{status} {self.timestamp.strftime('%Y-%m-%d %H:%M')} - {self.message[:50]}"


class AllowedIP(models.Model):
    """
    Model do zarządzania dozwolonymi adresami IP, które mają dostęp do aplikacji.
    Adresy IP są dynamicznie sprawdzane przez middleware.
    """
    ip_address = models.GenericIPAddressField(
        protocol='IPv4',
        unique=True,
        verbose_name="Adres IP",
        help_text="Adres IP, który ma mieć dostęp do aplikacji (np. 10.11.1.1)"
    )
    opis = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Opis",
        help_text="Krótki opis adresu IP (np. 'Serwer główny', 'Stanowisko 1')"
    )
    aktywny = models.BooleanField(
        default=True,
        verbose_name="Aktywny",
        help_text="Czy ten adres IP ma dostęp do aplikacji"
    )
    data_utworzenia = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )
    data_modyfikacji = models.DateTimeField(
        auto_now=True,
        verbose_name="Data modyfikacji"
    )

    class Meta:
        verbose_name = "Dozwolony adres IP"
        verbose_name_plural = "Dozwolone adresy IP"
        ordering = ['ip_address']
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['aktywny']),
        ]

    def __str__(self):
        opis_str = f" - {self.opis}" if self.opis else ""
        status = "✓" if self.aktywny else "✗"
        return f"{status} {self.ip_address}{opis_str}"
