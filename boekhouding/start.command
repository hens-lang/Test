#!/bin/bash
# Dubbelklik dit bestand op je Mac om de boekhouding te starten.
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python is nog niet geïnstalleerd."
  echo "Installeer het via https://www.python.org/downloads en dubbelklik daarna opnieuw op dit bestand."
  open "https://www.python.org/downloads/"
  read -p "Druk op Enter om te sluiten..."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Eerste keer: benodigdheden installeren (duurt ongeveer een minuut)..."
  python3 -m venv .venv || { read -p "Installatie mislukt. Druk op Enter om te sluiten..."; exit 1; }
  .venv/bin/pip install -q -r requirements.txt || { read -p "Installatie mislukt. Druk op Enter om te sluiten..."; exit 1; }
fi

echo "Boekhouding draait op http://localhost:5000"
echo "Laat dit venster open zolang je de app gebruikt. Sluiten = app stoppen."
(sleep 2 && open "http://localhost:5000") &
.venv/bin/python app.py
