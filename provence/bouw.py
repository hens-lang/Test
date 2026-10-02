#!/usr/bin/env python3
"""Bouwt de deelbare website.

    huis.json  (alle gegevens)
  + fotos/     (jullie foto's, namen zoals in huis.json -> galerij)
  + template.html
  = Sablet-VI.html  (één bestand, foto's zitten erin: zo door te sturen)

Gebruik:  python3 bouw.py
Pillow (pip install pillow) is optioneel: daarmee worden foto's verkleind
zodat het bestand licht blijft om te delen.
"""
import base64
import io
import json
import mimetypes
import re
import sys
from pathlib import Path

MAP = Path(__file__).resolve().parent
FOTO_MAP = MAP / "fotos"
MAX_PX = 1600
KWALITEIT = 80
EXTENSIES = {".jpg", ".jpeg", ".png", ".webp"}

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None


def foto_naar_data_uri(pad: Path) -> str:
    if Image is not None:
        with Image.open(pad) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((MAX_PX, MAX_PX))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=KWALITEIT, optimize=True, progressive=True)
            data, mime = buf.getvalue(), "image/jpeg"
    else:
        data = pad.read_bytes()
        mime = mimetypes.guess_type(pad.name)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def zoek_foto(naam: str):
    """Vind een foto op naam, ook als de extensie of hoofdletters afwijken."""
    exact = FOTO_MAP / naam
    if exact.exists():
        return exact
    stam = Path(naam).stem.lower()
    for p in FOTO_MAP.iterdir():
        if p.suffix.lower() in EXTENSIES and p.stem.lower() == stam:
            return p
    return None


def main():
    huis = json.loads((MAP / "huis.json").read_text(encoding="utf-8"))
    template = (MAP / "template.html").read_text(encoding="utf-8")
    FOTO_MAP.mkdir(exist_ok=True)

    fotos, gebruikt, ontbreekt = {}, set(), []
    for item in huis["galerij"]:
        pad = zoek_foto(item["bestand"])
        if pad:
            fotos[item["bestand"]] = foto_naar_data_uri(pad)
            gebruikt.add(pad.name)
        else:
            ontbreekt.append(item["bestand"])
    # Extra foto's in de map die niet in huis.json staan komen er ook bij (categorie "Overig").
    for pad in sorted(FOTO_MAP.iterdir()):
        if pad.suffix.lower() in EXTENSIES and pad.name not in gebruikt:
            fotos[pad.name] = foto_naar_data_uri(pad)

    # Controles, zodat data en pagina altijd op elkaar aansluiten.
    waarschuwingen = []
    kamer_ids = {k["id"] for k in huis["kamers"]}
    for g in huis["galerij"]:
        if g.get("ruimte") and g["ruimte"] not in kamer_ids:
            waarschuwingen.append(f"galerij '{g['bestand']}' verwijst naar onbekende ruimte '{g['ruimte']}'")
    for veld, waarde in huis["contact"].items():
        if "VUL_IN" in str(waarde):
            waarschuwingen.append(f"contact.{veld} is nog niet ingevuld (knop wordt verborgen)")
    for p in huis["tarieven"]["periodes"]:
        if p["van"] >= p["tot"]:
            waarschuwingen.append(f"tariefperiode '{p['naam']}' heeft 'van' na 'tot'")

    def js(obj):
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    html = template.replace("/*HUIS*/null", js(huis)).replace("/*FOTOS*/{}", js(fotos))
    html = html.replace("__TITEL__", f"{huis['naam']} · {huis['plaats']}, Provence")
    html = html.replace("__OMSCHRIJVING__", re.sub(r'["<>]', "", huis["intro"]))

    uit = MAP / f"{re.sub(r'[^A-Za-z0-9]+', '-', huis['naam']).strip('-')}.html"
    uit.write_text(html, encoding="utf-8")

    print(f"✓ {uit.name} gemaakt ({uit.stat().st_size / 1e6:.1f} MB, {len(fotos)} foto's)")
    if ontbreekt:
        print(f"  • {len(ontbreekt)} foto('s) nog niet in fotos/, er wordt een illustratie getoond:")
        for n in ontbreekt:
            print(f"      fotos/{n}")
    if Image is None and fotos:
        print("  • Tip: 'pip install pillow' maakt het bestand veel kleiner.")
    for w in waarschuwingen:
        print(f"  ! {w}")


if __name__ == "__main__":
    sys.exit(main())
