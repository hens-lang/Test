"""Maakt geanonimiseerde test-fixtures uit echte exports in data/inbox/.

    python tests/maak_fixtures.py

Houdt de HTML-structuur (kolommen, loadRecord, \\xa0, MAX-codes, dubbele opname-regels) intact,
maar leegt alle persoonsgegevens en neemt per bestand maximaal 40 rijen.
"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from link_data.parsers import herken, schoon  # noqa: E402

PII = {"bedrijf", "recording", "laatste interne memo", "aanhef", "achternaam", "e-mail", "functie",
       "huisnummer", "mobiel nummer", "plaats", "postcode", "straatnaam", "telefoonnummer", "tussenvoegsel",
       "voornaam", "website", "memo callcenter", "memo klant", "voicelog", "chat log", "laatste externe memo",
       "laatste historie externe memo", "laatste historie interne memo", "email adres afzender", "naam afzender",
       "email tekst", "recording transcriptie", "link naar ad libary", "referentie", "transfer number"}


def anonimiseer(bron: Path, doel: Path, max_rijen=40):
    soup = BeautifulSoup(bron.read_bytes().decode("utf-8", errors="replace"), "lxml")
    type_, tabel = herken(soup, bron)
    for s in soup.find_all(["script", "iframe"]):
        s.decompose()
    kop = [schoon(th.get_text()).lower() for th in (tabel.find("thead") or tabel).find("tr").find_all(["th", "td"])]
    rijen = (tabel.find("tbody") or tabel).find_all("tr")
    rijen = [r for r in rijen if r.find("td")]
    for i, tr in enumerate(rijen):
        if i >= max_rijen:
            tr.decompose()
            continue
        for j, td in enumerate(tr.find_all("td")):
            if j < len(kop) and kop[j] in PII:
                td.string = f"X{i}" if kop[j] == "bedrijf" else ""
    doel.write_text(str(soup), encoding="utf-8")
    return type_


if __name__ == "__main__":
    uit = ROOT / "tests" / "fixtures"
    uit.mkdir(exist_ok=True)
    gezien = set()
    for p in sorted((ROOT / "data" / "inbox").glob("*.xls")):
        m = re.search(r"(custom|PayableHoursPerDay)", p.name)
        if not m:
            continue
        t = anonimiseer(p, uit / f"tmp_{p.name}")
        kop_n = len(BeautifulSoup((uit / f"tmp_{p.name}").read_text(encoding="utf-8"), "lxml").find("tr").find_all("th"))
        naam = f"{'belexport' if t == 'A' else 'uren'}_{kop_n}kol.xls"
        if naam in gezien:
            naam = naam.replace(".xls", f"_{len(gezien)}.xls")
        gezien.add(naam)
        (uit / f"tmp_{p.name}").rename(uit / naam)
        print(naam, "<-", p.name)
