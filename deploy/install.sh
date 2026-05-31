#!/bin/bash
# install.sh — Linux Server Setup für StockCRASH_WarnAPP
# Getestet auf Ubuntu 22.04 / Debian 12 / Raspberry Pi OS

set -e

echo "========================================"
echo " StockCRASH_WarnAPP — Server Setup"
echo "========================================"

# Python prüfen
if ! command -v python3 &> /dev/null; then
    echo "Installiere Python3..."
    sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
fi

# Virtualenv erstellen
echo "Erstelle virtuelle Umgebung..."
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
echo "Installiere Python-Pakete..."
pip install --upgrade pip
pip install -r requirements.txt

# .env anlegen falls nicht vorhanden
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  WICHTIG: .env Datei erstellt — bitte jetzt befüllen:"
    echo "   nano .env"
    echo ""
fi

# Logs-Ordner
mkdir -p logs

# systemd Service installieren
echo "Installiere systemd Service..."
sudo cp deploy/crashwarn.service /etc/systemd/system/crashwarn.service

# Pfad im Service anpassen
INSTALL_DIR=$(pwd)
sudo sed -i "s|INSTALL_DIR|$INSTALL_DIR|g" /etc/systemd/system/crashwarn.service

sudo systemctl daemon-reload
sudo systemctl enable crashwarn

echo ""
echo "✅ Installation abgeschlossen!"
echo ""
echo "Nächste Schritte:"
echo "  1. .env befüllen:           nano .env"
echo "  2. Test-Check ausführen:    source venv/bin/activate && python main.py --test"
echo "  3. Pushover testen:         python main.py --notify-test"
echo "  4. Service starten:         sudo systemctl start crashwarn"
echo "  5. Logs beobachten:         sudo journalctl -u crashwarn -f"
echo ""
