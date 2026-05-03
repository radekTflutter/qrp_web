#!/bin/bash

# QRP Control System - Setup Script

echo "🚀 QRP Control System - Instalacja"
echo "===================================="
echo ""

# Sprawdź czy Python jest zainstalowany
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 nie jest zainstalowany!"
    exit 1
fi

echo "✅ Python 3 znaleziony: $(python3 --version)"
echo ""

# Utwórz wirtualne środowisko (jeśli nie istnieje)
if [ ! -d "venv" ]; then
    echo "📦 Tworzenie wirtualnego środowiska..."
    python3 -m venv venv
    echo "✅ Wirtualne środowisko utworzone"
else
    echo "✅ Wirtualne środowisko już istnieje"
fi

echo ""
echo "🔧 Aktywacja wirtualnego środowiska..."
source venv/bin/activate

echo ""
echo "📥 Instalacja zależności..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "🗄️  Tworzenie migracji..."
python manage.py makemigrations

echo ""
echo "📊 Zastosowanie migracji..."
python manage.py migrate

echo ""
echo "👤 Utwórz superużytkownika (opcjonalnie):"
echo "   python manage.py createsuperuser"
echo ""
echo "🚀 Uruchom serwer:"
echo "   python manage.py runserver"
echo ""
echo "✅ Instalacja zakończona!"
echo ""
echo "🌐 Panel administracyjny będzie dostępny pod adresem:"
echo "   http://localhost:8000/admin/"

