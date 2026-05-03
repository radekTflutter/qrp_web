# Generated manually for AllowedIP model

from django.db import migrations, models


def create_initial_allowed_ip(apps, schema_editor):
    """Utwórz początkowy adres IP 10.11.1.1"""
    AllowedIP = apps.get_model('qrp_app', 'AllowedIP')
    
    # Sprawdź czy już istnieje
    if not AllowedIP.objects.filter(ip_address='10.11.1.1').exists():
        AllowedIP.objects.create(
            ip_address='10.11.1.1',
            opis='Początkowy adres IP',
            aktywny=True
        )


def reverse_create_initial_allowed_ip(apps, schema_editor):
    """Cofnięcie - usuń początkowy adres IP"""
    AllowedIP = apps.get_model('qrp_app', 'AllowedIP')
    AllowedIP.objects.filter(ip_address='10.11.1.1').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('qrp_app', '0014_add_csv_export_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='AllowedIP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(help_text='Adres IP, który ma mieć dostęp do aplikacji (np. 10.11.1.1)', protocol='IPv4', unique=True, verbose_name='Adres IP')),
                ('opis', models.CharField(blank=True, help_text='Krótki opis adresu IP (np. \'Serwer główny\', \'Stanowisko 1\')', max_length=200, null=True, verbose_name='Opis')),
                ('aktywny', models.BooleanField(default=True, help_text='Czy ten adres IP ma dostęp do aplikacji', verbose_name='Aktywny')),
                ('data_utworzenia', models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')),
                ('data_modyfikacji', models.DateTimeField(auto_now=True, verbose_name='Data modyfikacji')),
            ],
            options={
                'verbose_name': 'Dozwolony adres IP',
                'verbose_name_plural': 'Dozwolone adresy IP',
                'ordering': ['ip_address'],
            },
        ),
        migrations.AddIndex(
            model_name='allowedip',
            index=models.Index(fields=['ip_address'], name='qrp_app_all_ip_addr_idx'),
        ),
        migrations.AddIndex(
            model_name='allowedip',
            index=models.Index(fields=['aktywny'], name='qrp_app_all_aktywny_idx'),
        ),
        migrations.RunPython(create_initial_allowed_ip, reverse_create_initial_allowed_ip),
    ]
