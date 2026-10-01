"""Genereert dashboard/index.html uit het model (één zelfstandig HTML-bestand, data ingebakken)."""
from __future__ import annotations

import json
from pathlib import Path

from link_data.config import ROOT, Config
from link_data.export import payload
from link_data.model import Model

SJABLOON = ROOT / "link_data" / "dashboard_template.html"
UITVOER = ROOT / "dashboard" / "index.html"


def bouw_dashboard(model: Model, cfg: Config, uitvoer: Path = UITVOER) -> Path:
    data = json.dumps(payload(model, cfg), ensure_ascii=False, separators=(",", ":"), default=str)
    data = data.replace("</", "<\\/")  # veilig binnen <script>
    html = SJABLOON.read_text(encoding="utf-8").replace("__DATA__", data)
    uitvoer.parent.mkdir(parents=True, exist_ok=True)
    uitvoer.write_text(html, encoding="utf-8")
    return uitvoer


if __name__ == "__main__":
    import run
    run.main(["--alleen-dashboard"])
