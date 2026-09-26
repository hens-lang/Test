#!/usr/bin/env python3
"""
LINK. | Verhalen bouwen

Leest content/verhalen/*.md en maakt:
  - verhaal-<slug>.html   (één pagina per verhaal, in de huisstijl)
  - verhalen.html         (overzicht met filters)
  - data/verhalen.js      (lijst voor de kaarten op de homepage)
  - sitemap.xml           (bijgewerkt, zonder concepten)

Gebruik:
  python3 tools/build-verhalen.py          # alles, concepten met label "Concept"
  python3 tools/build-verhalen.py --live   # concepten worden overgeslagen

Een verhaal begint met een kopje tussen --- regels:
  title, type (Partnerverhaal | Uit de praktijk | Visie), date (JJJJ-MM-DD),
  author, status (concept | live), excerpt, en optioneel sector.
"""
import glob
import html
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.linkgrp.nl"
LIVE = "--live" in sys.argv
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"]
TYPES = ["Partnerverhaal", "Uit de praktijk", "Visie"]
ARROW = ('<svg class="arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
         'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>')
DOT = '<span class="dot">.</span>'


def parse(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"Geen kopje (---) gevonden in {path}")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    meta["slug"] = os.path.splitext(os.path.basename(path))[0]
    meta["body"] = m.group(2).strip()
    meta.setdefault("status", "concept")
    if meta.get("type") not in TYPES:
        raise SystemExit(f"Onbekend type in {path}: {meta.get('type')}")
    words = len(re.findall(r"\w+", meta["body"]))
    meta["read"] = max(1, math.ceil(words / 200))
    y, mo, d = (int(x) for x in meta["date"].split("-"))
    meta["date_nl"] = f"{d} {MAANDEN[mo - 1]} {y}"
    meta["url"] = f"verhaal-{meta['slug']}.html"
    return meta


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def md(body):
    out, para, lst, quote = [], [], [], []

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if lst:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in lst) + "</ul>")
            lst.clear()
        if quote:
            first, rest = quote[0], quote[1:]
            cite = f"<cite>{inline(' '.join(rest))}</cite>" if rest else ""
            out.append(f"<blockquote><p>{inline(first)}</p>{cite}</blockquote>")
            quote.clear()

    for line in body.splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("### "):
            flush(); out.append(f"<h3>{inline(s[4:])}</h3>")
        elif s.startswith("## "):
            flush(); out.append(f"<h2>{inline(s[3:])}</h2>")
        elif s.startswith("- "):
            if para or quote:
                flush()
            lst.append(s[2:])
        elif s.startswith(">"):
            if para or lst:
                flush()
            quote.append(s.lstrip("> ").strip())
        else:
            if lst or quote:
                flush()
            para.append(s)
    flush()
    return "\n".join(out)


def head(title, desc, url, og_type="website", extra=""):
    t, d = html.escape(title), html.escape(desc)
    return f'''<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{SITE}/{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="nl_NL">
<meta property="og:site_name" content="LINK.">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{SITE}/{url}">
<meta property="og:image" content="{SITE}/assets/img/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#000000">
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="assets/img/apple-touch-icon.png">
<link rel="preload" href="assets/fonts/montserrat-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/css/fonts.css">
<link rel="stylesheet" href="assets/css/style.css">
{extra}</head>
<body>
<a class="skip" href="#main">Naar inhoud</a>

<main id="main">
'''


FOOT = '''
</main>

<script src="data/site.js"></script>
<script src="data/verhalen.js"></script>
<script src="assets/js/main.js"></script>
</body>
</html>
'''


def card(v):
    concept = '<span class="v-badge">Concept</span>' if v["status"] != "live" else ""
    return f'''<a class="v-card" href="{v['url']}" data-type="{html.escape(v['type'])}">
          <span class="v-type">{html.escape(v['type'])}{concept}</span>
          <h3>{html.escape(v['title'])}</h3>
          <p>{html.escape(v['excerpt'])}</p>
          <span class="v-meta">{v['date_nl']} · {v['read']} min lezen</span>
        </a>'''


CTA = f'''
  <section class="section cta" data-photo-host>
    <div class="orb" aria-hidden="true"></div>
    <div class="wrap cta-grid">
      <div>
        <p class="eyebrow reveal">Kennismaken</p>
        <h2 class="reveal">We drinken graag een kop koffie met je{DOT}</h2>
        <p class="reveal">Geen verkoopgesprek. Gewoon kennismaken, eerlijk vertellen wat we kunnen, en kijken of het klopt.</p>
        <div class="actions reveal">
          <a class="btn btn--light" href="contact.html">Plan een kennismaking {ARROW}</a>
          <a class="tel" data-c="phone" href="#"></a>
        </div>
      </div>
      <figure class="photo-frame reveal" data-photo-wrap><img data-photo="koffie" alt="" sizes="(min-width: 960px) 34vw, 100vw"></figure>
    </div>
  </section>
'''


def story_page(v, others):
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": v["title"],
          "description": v["excerpt"], "datePublished": v["date"], "inLanguage": "nl-NL",
          "author": {"@type": "Person" if v.get("author", "") != "LINK." else "Organization", "name": v.get("author", "LINK.")},
          "publisher": {"@type": "Organization", "name": "LINK.", "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/img/logo-zwart.png"}},
          "mainEntityOfPage": f"{SITE}/{v['url']}"}
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
    if v["status"] != "live":
        extra += '<meta name="robots" content="noindex">\n'
    concept = ('<p class="v-concept">Concept: nog niet gepubliceerd. Dit verhaal wacht op goedkeuring.</p>'
               if v["status"] != "live" else "")
    related = "".join(card(o) for o in others[:2])
    return head(f"{v['title']} | LINK.", v["excerpt"], v["url"], "article", extra) + f'''
  <article class="story">
    <header class="story-hero">
      <div class="wrap story-narrow">
        <a class="story-back" href="verhalen.html">Alle verhalen</a>
        <p class="eyebrow">{html.escape(v['type'])}</p>
        <h1>{html.escape(v['title'])}</h1>
        <p class="story-lead">{html.escape(v['excerpt'])}</p>
        <p class="story-meta"><strong>{html.escape(v.get('author', 'LINK.'))}</strong><span>{v['date_nl']}</span><span>{v['read']} min lezen</span></p>
        {concept}
      </div>
    </header>
    <div class="wrap story-narrow story-body">
{md(v['body'])}
    </div>
  </article>

  <section class="section--tight">
    <div class="wrap">
      <div class="v-head"><h2>Meer verhalen{DOT}</h2><a class="link-arrow" href="verhalen.html">Alle verhalen</a></div>
      <div class="v-grid">
        {related}
      </div>
    </div>
  </section>
''' + CTA + FOOT


def overview(items):
    chips = '<button type="button" class="v-chip" aria-pressed="true" data-filter="*">Alles</button>' + "".join(
        f'<button type="button" class="v-chip" aria-pressed="false" data-filter="{t}">{t}</button>' for t in TYPES)
    cards = "\n        ".join(card(v) for v in items)
    return head("Verhalen | LINK.",
                "Partnerverhalen, inzichten uit de praktijk en de visie van LINK. op B2B acquisitie. Geen ruis, wel wat we elke dag horen aan de telefoon.",
                "verhalen.html") + f'''
  <section class="page-hero">
    <div class="big-dot" aria-hidden="true"></div>
    <div class="wrap" style="position:relative">
      <p class="eyebrow reveal">Verhalen</p>
      <h1 class="reveal">Wat we horen aan de telefoon{DOT}</h1>
      <p class="lead reveal" style="--d:.15s">Wat we elke dag horen aan de telefoon, wat het onze partners oplevert en hoe wij naar de markt kijken. Geen ruis, wel inhoud.</p>
    </div>
  </section>

  <section class="section" style="padding-top:0">
    <div class="wrap">
      <div class="v-filters" role="group" aria-label="Filter op soort verhaal">{chips}</div>
      <div class="v-grid" data-v-list>
        {cards}
      </div>
    </div>
  </section>
''' + CTA + FOOT


def main():
    items = [parse(p) for p in glob.glob(os.path.join(ROOT, "content/verhalen/*.md"))]
    if LIVE:
        items = [v for v in items if v["status"] == "live"]
    items.sort(key=lambda v: v["date"], reverse=True)

    for f in glob.glob(os.path.join(ROOT, "verhaal-*.html")):
        os.remove(f)
    for v in items:
        others = [o for o in items if o is not v]
        open(os.path.join(ROOT, v["url"]), "w", encoding="utf-8").write(story_page(v, others))
    open(os.path.join(ROOT, "verhalen.html"), "w", encoding="utf-8").write(overview(items))

    lst = [{k: v[k] for k in ("title", "type", "date", "date_nl", "excerpt", "status", "read", "url")} for v in items]
    open(os.path.join(ROOT, "data/verhalen.js"), "w", encoding="utf-8").write(
        "/* Gegenereerd door tools/build-verhalen.py. Niet met de hand aanpassen. */\n"
        "window.LINK_VERHALEN = " + json.dumps(lst, ensure_ascii=False, indent=2) + ";\n")

    pages = [("", "1.0"), ("diensten.html", "0.9"), ("over-link.html", "0.8"),
             ("verhalen.html", "0.8"), ("contact.html", "0.9")]
    pages += [(v["url"], "0.7") for v in items if v["status"] == "live"]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{SITE}/{u}</loc><priority>{p}</priority></url>" for u, p in pages]
    sm.append("</urlset>")
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm) + "\n")

    print(f"{len(items)} verhalen gebouwd" + (" (alleen live)" if LIVE else " (concepten met label)"))


if __name__ == "__main__":
    main()
