# LINK. — website

Herbouw van de LINK.-website (persoonlijke B2B-acquisitie) volgens
`DESIGN-DIRECTION.md`. Gebouwd met **Astro + TypeScript**: statische output,
één set designtokens, herbruikbare componenten, werkend contactformulier en
cookie-consent.

> De oorspronkelijke HTML-prototypes waren designreferentie, geen productiecode.
> Deze codebase implementeert de designrichting opnieuw, niet één-op-één de oude
> opmaak.

## Snel starten

```bash
npm install
cp .env.example .env      # vul PUBLIC_WEB3FORMS_KEY in
npm run dev               # http://localhost:4321
npm run build             # productie-build naar dist/
npm run preview           # bekijk de build lokaal
```

Node 18+ vereist (getest op Node 22).

## Structuur

```
src/
  layouts/Base.astro          # <head>, SEO/OG per pagina, nav + footer + consent
  components/
    Nav, Footer, Logo, Icon   # gedeelde UI
    Button/SectionHeading/Statement/Split   # de 3 sectietypes + helpers
    Figure.astro              # fotocontainer (aspect-ratio, blur-optie, placeholder)
    CookieConsent.astro       # AVG-consent; laadt Apollo pas na toestemming
    widgets/                  # Agenda, Pipeline, Timeline, TariefCalculator
  pages/                      # index, aanpak, diensten, verhaal, contact, bedankt, 404
  styles/tokens.css           # ÉÉN bron van designtokens
  styles/global.css           # reset, typografie, sectietypes, reveal, nav-drawer
  lib/site.ts                 # vaste gegevens, navigatie, form/Apollo-config
  scripts/app.ts              # nav-drawer, scroll, reveal, parallax
public/assets/                # foto's, favicons (zie PLAATS-FOTOS-HIER.md)
```

## Designsysteem

- **Tokens** staan alleen in `src/styles/tokens.css`. Geen inline `<style>` per
  pagina met eigen kleuren; component-stijlen zijn gescoped in de `.astro`-files.
- **De punt** (`.punc`, blauw) markeert een einde/moment — vooral op de h1.
- **Instrument Serif italic** (`.it`) alleen als accent, max. één keer per scherm.
- **Monospace** voor labels, nummers, statussen (het "rapportachtige" laagje).
- **Radii** vrijwel recht: knoppen 2px, kaarten 3px, grote donkere panelen 28px.
- **Sectietypes**: Statement (rustpunt), Split (werkpaard), Reeks (bovenlijn +
  monospace-nummer, geen kaarten).

## Contactformulier

De tarief-calculator (`components/widgets/TariefCalculator.astro`) verzendt echt
via [Web3Forms](https://web3forms.com):

- Zet `PUBLIC_WEB3FORMS_KEY` in `.env` (key gekoppeld aan `info@linkgrp.nl`).
- Ingebouwde **honeypot** tegen spam + client-side validatie (naam + e-mail).
- Succes → redirect naar `/bedankt`. Autoresponder is in te stellen in Web3Forms.
- Zonder key blijft de flow werken maar wordt niets verzonden (met console-waarschuwing).

Wil je een eigen backend i.p.v. Web3Forms? Vervang de `submit()`-fetch door een
POST naar je eigen endpoint (bv. een serverless functie met adapter).

## Cookie-consent & Apollo (AVG)

De Apollo website-tracker laadt **pas na toestemming**. De keuze wordt in
`localStorage` bewaard (`link-consent-v1`). Zie `components/CookieConsent.astro`.
App-id staat in `lib/site.ts`.

## Foto's

Zie `public/assets/PLAATS-FOTOS-HIER.md` voor de exacte bestandsnamen en waar ze
landen. Zolang een foto ontbreekt toont `Figure` een nette placeholder.
Portaal-screenshots worden met ~2px blur getoond (klantnamen onleesbaar).

## Nog aan te leveren door de eigenaar (niet verzonnen)

- Klantquote met naam, functie en bedrijf.
- Eén echt resultaatcijfer dat gedeeld mag worden.
- Klantlogo's, of het besluit dat die er niet komen.
- Definitieve algemene voorwaarden en privacyverklaring.

De plekken hiervoor kunnen eenvoudig als extra sectie/component worden
toegevoegd zodra het materiaal er is.

## Deploy

Statische output in `dist/` — te hosten op elke statische host (Netlify,
Vercel, Cloudflare Pages, of gewoon Apache/Nginx). URL's zijn extensieloos
(`/aanpak`), net als de oude `.htaccess`-rewrite.
