# LINK. Belprestatie- en kostprijsdashboard

Eén pipeline van Steam Connect (Belstat) exports en bellerfacturen naar één dashboard.
Alles draait op dezelfde dataset (`data/link.db`) en dezelfde configuratie (`config/`).

## Wekelijks verversen

1. Zet nieuwe bestanden in `data/inbox/`. De bestandsnaam maakt niet uit.
   - belexports (`custom_*.xls`, Management module)
   - urenexport (`PayableHoursPerDay_*.xls`)
   - historie-export met alle contactmomenten (zodra beschikbaar)
   - facturen van bellers (PDF)
   - verkoopfacturen aan klanten (PDF), of een lijst `verkoopfacturen_mailbox.csv`
     (`factuurnr;factuurdatum;debiteur;bedrag_incl;opmerking`)
2. Draai:

   ```
   python run.py
   ```

3. Open `dashboard/index.html` in de browser. Je hebt geen server nodig; voor de grafieken is wel internet nodig (Chart.js en lettertypes).

Oude exports mag je laten staan. Dezelfde export twee keer inlezen geeft geen dubbele data. Een nieuwere export van hetzelfde record of dezelfde dag werkt de bestaande regel bij.

`python run.py --opnieuw` bouwt de database helemaal opnieuw op uit alles in `data/inbox/`.

## Eenmalig installeren

```
pip install -r requirements.txt
```

## Wat waar staat

| Pad | Inhoud |
|---|---|
| `config/klanten.yaml` | opdrachtgevers, campagne-PID's, fees, targets, belstart, wat telt als resultaat |
| `config/bellers.yaml` | bellers, aliassen (zoals in de exports), tarieven, vaste vergoeding, factuurafzender |
| `config/instellingen.yaml` | werkperiode-anker, overige kosten per maand, focusdrempel, scenario-tarieven, opbrengstbasis |
| `config/kosten.yaml` | facturen voor overige kosten (Steam, AdHocData, Apollo, hosting) |
| `link_data/parsers.py` | herkent en leest alle exporttypes (ook bruikbaar voor de klantrapportages) |
| `link_data/store.py` | SQLite-opslag met ontdubbeling |
| `link_data/model.py` | schone tabellen, kosten, verdeelsleutel, opbrengst, targets, datakwaliteit |
| `link_data/export.py` | CSV-export en dashboarddata |
| `build_dashboard.py` | schrijft `dashboard/index.html` |
| `run.py` | het ene commando |
| `data/export/` | CSV's (puntkomma, decimale komma) voor het Omzet Dashboard in Google Sheets |

## Hoe het rekent

- **Uren**: `Te betalen` uit de urenexport.
- **Kosten ZZP**: voor een week mét factuur geldt het gefactureerde bedrag. Voor een week zonder factuur is het een schatting: Steam-uren x tarief. Facturen zonder weeknummer gaan naar de week van de factuurdatum (do t/m zo) of naar de week ervoor (ma t/m wo).
- **Kosten eigenaren**: een vaste vergoeding per maand. Die wordt verdeeld over de betaalde uren van die maand.
- **Verdeelsleutel**: Steam splitst uren niet per campagne. Daarom worden de uren van een beller op een dag verdeeld naar rato van zijn belregels per opdrachtgever die dag. Een dag zonder belregels komt op "Niet toegerekend".
- **Opbrengst**: wat echt gefactureerd is. Een verkoopfactuur telt verdeeld over zijn periode (een factuur zonder periode: 28 dagen vanaf de factuurdatum), tot de peildatum. Met `opbrengst_basis: facturen_en_schatting` vult het model dagen zonder factuur aan met fee / 28.
- **Werkperiodes**: volgens de verkoopfactuur als die er is ("werkperiode 4, periode ..."), anders vanaf de belstart.
- **Status klant**: `actief`, `pauze` of `gestopt`. Alleen actieve klanten tellen mee in targets en scenario.
- **Overige kosten**: facturen uit `kosten.yaml` (een jaarlicentie wordt per dag verdeeld); maanden zonder factuur krijgen het laatst bekende bedrag als schatting.
- **Resultaat**: per opdrachtgever volgens `telt_als_resultaat`.
- **Werkperiode**: 4 weken. Per opdrachtgever tellen die vanaf de eigen belstart; in de filters vanaf `werkperiode_anker`.

### Belexport tegenover historie-export

De belexport (Type A) toont per record alleen het **laatste** contactmoment. De funnel (bereik, conversie, resultaten) klopt daarmee, maar de analyse per uur van de dag en de focus-index zijn vertekend. Het dashboard toont dan een waarschuwing. Zet de historie-export in de inbox: de parser herkent hem aan de kolommen (agent, datum & tijd, resultaatcode), en zijn regels gaan vóór de belexport.

## Nieuwe opdrachtgever, beller of campagne

- Staat er een onbekende PID in een export, dan verschijnt die op het tabblad **Datakwaliteit** onder "Niet gekoppelde campagne-PID's", met de campagnenaam uit de export. Zet de PID bij de juiste klant in `klanten.yaml`.
- Een onbekende agentnaam of factuurafzender verschijnt daar ook. Voeg die toe als alias of `factuur_afzenders` in `bellers.yaml`.

## Tests

```
python -m pytest
```

De tests draaien op geanonimiseerde uitsneden van echte exports (`tests/fixtures/`). Liggen er echte bestanden in `data/inbox/`, dan worden die ook getest. Nieuwe fixtures maak je met `python tests/maak_fixtures.py`: die haalt namen, telefoonnummers, adressen en memo's weg.

`data/inbox/`, `data/link.db`, `data/export/` en `dashboard/index.html` staan niet in git, omdat ze persoonsgegevens en bedrijfscijfers bevatten.
