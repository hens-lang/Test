"""Genereert dashboard/index.html uit het model (één zelfstandig HTML-bestand, data ingebakken)."""
from __future__ import annotations

import json
from pathlib import Path

from link_data.config import ROOT, Config
from link_data.export import payload
from link_data.model import Model

SJABLOON = ROOT / "link_data" / "dashboard_template.html"
UITVOER = ROOT / "dashboard" / "index.html"
# Versie zonder <html>/<head>/<body>-skelet, voor publicatie als privépagina op claude.ai
PAGINA = ROOT / "dashboard" / "link-dashboard.html"


def bouw_dashboard(model: Model, cfg: Config, uitvoer: Path = UITVOER) -> Path:
    data = json.dumps(payload(model, cfg), ensure_ascii=False, separators=(",", ":"), default=str)
    data = data.replace("</", "<\\/")  # veilig binnen <script>
    html = SJABLOON.read_text(encoding="utf-8").replace("__DATA__", data)
    uitvoer.parent.mkdir(parents=True, exist_ok=True)
    uitvoer.write_text(html, encoding="utf-8")
    if uitvoer == UITVOER:
        PAGINA.write_text(_zonder_skelet(html), encoding="utf-8")
    return uitvoer


def _zonder_skelet(html: str) -> str:
    """Haalt doctype, html-, head- en body-tags weg; title, links, scripts en styles blijven staan."""
    import re
    for patroon in (r"<!doctype[^>]*>", r"</?html[^>]*>", r"</?head>", r"<body[^>]*>", r"</body>",
                    r'<meta charset="utf-8">', r'<meta name="viewport"[^>]*>'):
        html = re.sub(patroon, "", html, flags=re.I)
    return html.strip() + "\n"


if __name__ == "__main__":
    import run
    run.main(["--alleen-dashboard"])
