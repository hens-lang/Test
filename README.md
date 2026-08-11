# Vangst — design-prototype

> **Jij staat te werken, wij vangen je klanten.**

Klikbaar front-end prototype voor **Vangst**, een AI-assistent voor kleine
Nederlandse ondernemers (schilders, kappers, hoveniers, rijscholen, personal
trainers). Vangst vangt elke klantaanvraag op — via WhatsApp, het
websiteformulier of een gemiste oproep — antwoordt binnen een minuut in de toon
van de ondernemer, plant afspraken in de agenda en volgt openstaande offertes
vriendelijk op.

Dit is **puur een design-demo**: geen backend, geen echte data. Alles draait op
verzonnen voorbeeldgegevens van één bedrijf: **Schildersbedrijf Van Dijk uit
Gouda**. Bedoeld om te laten zien tijdens verkoopgesprekken met ondernemers.

## Starten

Geen installatie of build nodig — het is gewoon HTML, CSS en JavaScript.

**Optie 1 — dubbelklikken**
Open `index.html` in je browser.

**Optie 2 — via een lokale server** (aanbevolen, voorkomt eventuele browser-beperkingen)

```bash
# In de projectmap:
python3 -m http.server 8000
```

Open daarna **http://localhost:8000** in je browser.

> Tip: bekijk het in een smal venster of via de mobiele weergave van je browser
> (F12 → toggle device toolbar). De app is mobiel-first ontworpen, maar staat ook
> netjes op desktop.

## Wat zit erin

### Landingspagina (`index.html`)
- De kernzin groot bovenaan
- Drie blokken: *Nooit meer een aanvraag missen* / *Afspraken plannen zichzelf* /
  *Offertes worden opgevolgd*
- Een voorbeeldgesprek als telefoon-mockup
- Drie prijstredes: **Start €39** · **Groei €79** · **Max €129** per maand
  (maandelijks opzegbaar, 14 dagen gratis)
- Eén duidelijke knop: **Probeer gratis** → opent het app-prototype

### App-prototype (`app.html`)
Alle schermen zijn klikbaar aan elkaar gekoppeld:

1. **Onboarding** (3 stappen) — branche kiezen, bedrijf omschrijven, kanalen
   koppelen (mock-knoppen)
2. **Dashboard** — grote omzetteller *"Deze maand opgevangen: €2.340"* met
   14 aanvragen / 6 afspraken / 3 offertes open, plus recente aanvragen
3. **Inbox** — alle gesprekken uit alle kanalen met kanaal-icoontje en status
4. **Gespreksweergave** — WhatsApp-achtig gesprek waarin de AI-berichten een
   `⚡ AI`-label hebben, met *"Zelf overnemen"* en een voorgesteld antwoord dat je
   met één tik verstuurt
5. **Afspraken** — agendaweek met geplande afspraken, elk met bron
   (*"via WhatsApp geboekt"*)
6. **Opvolging** — openstaande offertes met geplande automatische opvolging en
   een aan/uit-schakelaar per item
7. **Instellingen** — toon van de assistent, kennisbank en kanalen aan/uit

## Bestanden

| Bestand | Wat |
|---|---|
| `index.html` | Landingspagina |
| `app.html` | Het app-prototype (alle 7 schermen) |
| `styles.css` | Alle vormgeving (design-systeem) |
| `app.js` | Navigatie tussen schermen + dummy-gesprekken |

## Klikroutes om te demonstreren

- Landing → **Probeer gratis** → onboarding → **Start met Vangst** → dashboard
- Dashboard → tik op een aanvraag → gespreksweergave → **Versturen** of
  **Zelf overnemen**
- Onderbalk: Start · Inbox · Afspraken · Opvolging · Meer (instellingen)
- Opvolging → zet een schakelaar uit/aan
- Instellingen → **Terug naar de website**

---

*Alle namen, berichten en bedragen zijn verzonnen voorbeeldgegevens.*
