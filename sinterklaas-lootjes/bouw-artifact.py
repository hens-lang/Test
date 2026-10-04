#!/usr/bin/env python3
"""Maakt van index.html + lootjes.js één los bestand (voor de Claude-artifact-versie).

Gebruik: python3 bouw-artifact.py [uitvoerbestand]
"""
import pathlib
import re
import sys

hier = pathlib.Path(__file__).parent
html = (hier / 'index.html').read_text(encoding='utf-8')
js = (hier / 'lootjes.js').read_text(encoding='utf-8')

html = html.replace('<script src="lootjes.js"></script>', '<script>\n' + js + '</script>')
# Het artifact levert zelf doctype/html/head/body; wij houden alleen de inhoud.
html = re.sub(r'<!doctype html>\s*', '', html, flags=re.I)
html = re.sub(r'</?(html|head|body)[^>]*>\s*', '', html)
html = re.sub(r'<meta[^>]*>\s*', '', html)

uit = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else hier / 'dist' / 'sinterklaas-lootjes.html'
uit.parent.mkdir(parents=True, exist_ok=True)
uit.write_text(html, encoding='utf-8')
print('Geschreven:', uit)
