# Generated manually

from django.db import migrations, models
import django.db.models.deletion


def set_default_typ_kontroli(apps, schema_editor):
    """Ustawia domyślny typ kontroli dla istniejących rekordów bez typu kontroli"""
    Pomiar = apps.get_model('qrp_app', 'Pomiar')
    Wada = apps.get_model('qrp_app', 'Wada')
    TypKontroli = apps.get_model('qrp_app', 'TypKontroli')
    
    # Znajdź pierwszy aktywny typ kontroli
    default_typ = TypKontroli.objects.filter(aktywny=True).order_by('kolejnosc', 'id').first()
    
    if default_typ:
        # Ustaw dla pomiarów bez typu kontroli
        Pomiar.objects.filter(typ_kontroli__isnull=True).update(typ_kontroli=default_typ)
        
        # Ustaw dla wad bez typu kontroli
        Wada.objects.filter(typ_kontroli__isnull=True).update(typ_kontroli=default_typ)


def reverse_set_default_typ_kontroli(apps, schema_editor):
    """Cofnięcie - nie trzeba nic robić, bo wracamy do nullable"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('qrp_app', '0011_add_through_models_for_customization'),
    ]

    operations = [
        # Krok 1: Ustaw domyślny typ kontroli dla istniejących rekordów
        migrations.RunPython(set_default_typ_kontroli, reverse_set_default_typ_kontroli),
        # Krok 2: Zmień pole na wymagane (non-nullable)
        migrations.AlterField(
            model_name='pomiar',
            name='typ_kontroli',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pomiary',
                to='qrp_app.typkontroli',
                verbose_name='Typ kontroli'
            ),
        ),
        migrations.AlterField(
            model_name='wada',
            name='typ_kontroli',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='wady',
                to='qrp_app.typkontroli',
                verbose_name='Typ kontroli'
            ),
        ),
    ]
