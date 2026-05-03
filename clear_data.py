#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qrp_project.settings')
django.setup()

from qrp_app.models import Pomiar, Wada
from django.conf import settings
from pathlib import Path

# Statystyki
pomiary = Pomiar.objects.all()
wady = Wada.objects.all()
print(f'Znaleziono {pomiary.count()} pomiarów i {wady.count()} wad')

# Ścieżka do mediów
media_root = Path(settings.MEDIA_ROOT)
deleted_pics = 0

# Usuwanie pomiarów i zdjęć
deleted_pomiary = 0
for pomiar in pomiary:
    if pomiar.zdjecie:
        img_path = media_root / pomiar.zdjecie.name
        if img_path.exists():
            try:
                img_path.unlink()
                deleted_pics += 1
            except Exception as e:
                print(f'Błąd przy usuwaniu {img_path}: {e}')
    pomiar.delete()
    deleted_pomiary += 1

print(f'Usunięto {deleted_pomiary} pomiarów')

# Usuwanie wad i zdjęć
deleted_wady = 0
for wada in wady:
    if wada.zdjecie:
        img_path = media_root / wada.zdjecie.name
        if img_path.exists():
            try:
                img_path.unlink()
                deleted_pics += 1
            except Exception as e:
                print(f'Błąd przy usuwaniu {img_path}: {e}')
    wada.delete()
    deleted_wady += 1

print(f'Usunięto {deleted_wady} wad')
print(f'Usunięto łącznie {deleted_pics} zdjęć')
print('Gotowe!')
