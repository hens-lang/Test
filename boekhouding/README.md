# Boekhouding: ons eigen "Exact", maar dan automatisch

Facturen komen vanzelf binnen, worden automatisch gelezen en geboekt, en **jij keurt alleen goed**.
Direct daarna staat de betaling klaar in je ABN AMRO-app; één keer bevestigen met Face ID en klaar.
Bankmutaties komen automatisch binnen en facturen gaan vanzelf op betaald.

Alles zit in één database: relaties, facturen, grootboek, betalingen en bank zijn aan elkaar gekoppeld.

## Starten op een Mac

1. Installeer Python via https://www.python.org/downloads (eenmalig).
2. Dubbelklik op **`start.command`**. De eerste keer: rechtermuisknop → Open.
3. De app opent in je browser op http://localhost:5000. Laat het zwarte venster open zolang je werkt.

Eerst rondkijken met voorbeelddata? Open vóór de eerste start een Terminal in de map `boekhouding` en typ
`.venv/bin/python demo.py` (werkt alleen bij een lege administratie; begin daarna opnieuw door de map `data/` te verwijderen).

## Zo werkt het

```
 Mailbox / upload / map                       ABN AMRO (via Ponto)
         │                                           ▲   │
         ▼                                           │   │ mutaties (elk uur)
 Automatisch lezen ──► Leverancier herkennen ──► Goedkeuren ──► Bevestigen in ABN-app
 (e-factuur exact,     + IBAN-fraudecheck        (1 klik)         (Face ID)
  pdf/foto via AI)     + grootboekrekening           │                │
                                                     ▼                ▼
                                              Journaalpost     Afgeletterd → betaald
```

| Stap | Wat de app doet | Wat jij doet |
|---|---|---|
| Binnenkomst | Haalt facturen op uit de factuurmailbox (elke 5 min), uit uploads (slepen) en uit `data/inbox/` | niets |
| Lezen | E-facturen (UBL) exact; pdf's en foto's via Claude (AI). Herkent creditnota's, incasso's en al betaalde facturen | niets |
| Leverancier | Zoekt op IBAN, KvK, btw-nummer of naam; maakt nieuwe leveranciers zelf aan | bij een nieuwe leverancier even controleren |
| Controle | Dubbele facturen, bedragen die niet optellen, lage zekerheid en **een afwijkend IBAN (factuurfraude)** worden gemarkeerd | waarschuwingen lezen |
| Goedkeuren | Vertrouwde leveranciers onder hun limiet worden automatisch goedgekeurd | de rest goedkeuren (1 klik of alles tegelijk) |
| Boeken | Kosten, voorbelasting en crediteuren worden direct geboekt (dubbel boekhouden) | niets |
| Betalen | Zet de betaling klaar in je ABN-app, uit te voeren kort voor de vervaldatum (of direct). Creditnota's worden verrekend | bevestigen in de ABN-app |
| Bank | Haalt elk uur mutaties op en koppelt ze aan facturen (referentie, bedrag, IBAN, naam) | alleen wat niet automatisch lukt |
| Verkoop | Factuur maken, mailen als pdf **en e-factuur**, betaling herkennen, automatisch herinneren na 7 en 21 dagen | factuur aanmaken |
| Rapportage | Winst & verlies, balans, grootboekkaarten, btw-aangifte per kwartaal (rubrieken 1a t/m 5g) | aangifte overnemen |
| Overzicht | Elke ochtend een mail met wat op je wacht; alles in het logboek | mail lezen |

**Veiligheid bij betalen:** er wordt altijd betaald naar het *bekende* IBAN van een leverancier. Staat er op een
factuur ineens een ander rekeningnummer, dan krijg je een rode waarschuwing en wordt er niet automatisch
goedgekeurd. Automatisch goedkeuren gebeurt alleen bij leveranciers met een geverifieerd IBAN, onder hun limiet,
zonder waarschuwingen. En elke betaling bevestig je zelf in je ABN-app.

## Koppelingen instellen

Alle sleutels en wachtwoorden staan in **`config.env`** (wordt bij de eerste start aangemaakt uit
`config.env.voorbeeld`). Na het aanpassen: app herstarten. Zonder koppelingen werkt alles ook,
alleen met meer handwerk (uploaden in plaats van mailbox, betaalbestand in plaats van ABN-app).

### 1. Facturen lezen met AI (Claude)
1. Maak een account op https://console.anthropic.com en maak onder *API keys* een sleutel aan.
2. Zet hem in `config.env`: `ANTHROPIC_API_KEY=sk-ant-...`

Kosten: een paar cent per factuur. Zonder sleutel worden e-facturen (UBL) nog steeds volledig
automatisch gelezen, pdf's met eenvoudige tekstherkenning (altijd controleren).

### 2. Factuurmailbox
1. Maak een apart adres aan, bijv. `facturen@jullie-domein.nl`, en vraag leveranciers daar te factureren.
2. Vul `IMAP_HOST`, `IMAP_GEBRUIKER` en `IMAP_WACHTWOORD` in (Microsoft 365: `outlook.office365.com`,
   Gmail: `imap.gmail.com` met een app-wachtwoord).

### 3. Uitgaande mail (facturen, herinneringen, ochtendsamenvatting)
Vul `SMTP_HOST`, `SMTP_GEBRUIKER`, `SMTP_WACHTWOORD` in (Microsoft 365: `smtp.office365.com`, poort 587).

### 4. ABN AMRO via Ponto
Europese regels (PSD2) staan niet toe dat software zelfstandig geld van een ABN-rekening afschrijft. Ponto
(Isabel Group, onder toezicht van de Nationale Bank van België) is de erkende tussenpartij: de app zet de
betaling klaar, jij bevestigt hem met de ABN-app.

1. Maak een account op https://myponto.com en koppel daar je ABN AMRO-rekening.
2. Ga naar *Integrations* → maak een integratie voor je eigen organisatie. Noteer **client ID** en
   **client secret**, en download het **certificaat** en de **private key**.
3. Zet `certificate.pem` en `private_key.pem` in de map `boekhouding/` en vul `PONTO_CLIENT_ID`,
   `PONTO_CLIENT_SECRET` (en eventueel `PONTO_KEY_WACHTWOORD`) in `config.env` in.
4. Voeg in Ponto de redirect-URL toe die op de pagina *Instellingen* in de app staat.
5. In de app: **Instellingen → ABN AMRO koppelen**, inloggen bij Ponto, toestemming geven.
6. Eenmalig: **Betalen activeren**.

Tip: test eerst met `PONTO_OMGEVING=sandbox` en de sandbox-gegevens uit het Ponto-dashboard.

## Beveiliging

- Zet `APP_WACHTWOORD` in `config.env` zodra iemand anders bij je computer kan, en altijd als de app
  online komt te staan.
- `config.env`, de certificaten en de map `data/` bevatten gevoelige gegevens en staan niet in git.
- Maak regelmatig een back-up van de map `data/` (de administratie) en `uploads/` (de facturen).

## Technisch

| Bestand | Inhoud |
|---|---|
| `db.py` | Databaseschema (SQLite), rekeningschema (RGS-light), instellingen, migraties |
| `logica.py` | Bedrijfsregels: inkoop, goedkeuren, verkoop, afletteren, overzichten |
| `grootboek.py` | Journaalposten, storno's, W&V, balans, btw-aangifte |
| `intake.py` | Documenten ontvangen (upload, mailbox, map), UBL lezen, leverancier en fraudecontrole |
| `ai.py` | Factuur uitlezen met Claude (gestructureerde output) |
| `betalen.py` | Betaalvoorstel, verrekenen, betaalopdrachten (ABN via Ponto of SEPA-bestand) |
| `ponto.py` | Ponto Connect: OAuth, rekeningen, mutaties, bulkbetalingen |
| `sepa.py`, `bankimport.py` | SEPA pain.001-export, CAMT.053/CSV-import |
| `factuurdocument.py` | Verkoopfactuur als pdf en als e-factuur (UBL / NLCIUS) |
| `mail.py` | Facturen mailen, herinneringen, dagelijkse samenvatting |
| `planner.py` | Achtergrondtaken (mailbox, bank, herinneringen) |
| `app.py`, `templates/`, `static/` | Webschermen |

Tests (de hele keten, inclusief een nagebootste Ponto-server): `.venv/bin/python -m pytest`

**Nog te verifiëren met echte accounts:** de Ponto-koppeling is gebouwd volgens de Ponto Connect-API en
getest tegen een nagebootste server, maar nog niet tegen de echte Ponto-omgeving. Test die eerst in de
Ponto-sandbox. Hetzelfde geldt voor het uitlezen met Claude: pas met een API-sleutel zie je hoe goed het
werkt op jullie eigen facturen.
