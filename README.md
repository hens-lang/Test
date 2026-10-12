# LINK. Belprestatie- en kostprijsdashboard

Eén pipeline van Steam Connect (Belstat) exports en bellerfacturen naar één dashboard.
Alles draait op dezelfde dataset (`data/link.db`) en dezelfde configuratie (`config/`).

## Wekelijks verversen

1. Zet nieuwe bestanden in `data/inbox/`. De bestandsnaam maakt niet uit.
   - belexports (`custom_*.xls`, Management module)
   - urenexport (`PayableHoursPerDay_*.xls`)
   - historie-export met alle contactmomenten (zodra beschikbaar)
   - contactstatistieken per agent (`contactstatistics_agents_*.xls`): alle pogingen en beltijd per campagne
   - facturen van bellers (PDF)
   - verkoopfacturen aan klanten (PDF), of een lijst `verkoopfacturen_mailbox.csv`
     (`factuurnr;factuurdatum;debiteur;bedrag_incl;opmerking`)
2. Draai:

   ```
   python run.py
   ```

3. Open `dashboard/index.html` in de browser. Het KPI-plan (Nu tegenover Moet per opdrachtgever) staat los in `dashboard/kpi-plan.html`, met dezelfde data en berekeningen. Je hebt geen server nodig; voor de grafieken is wel internet nodig (Chart.js en lettertypes).

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

- **Handmatige resultaten**: `config/handmatig.yaml` voor een resultaat dat nog niet in een belexport staat. Telt direct mee en vervalt vanzelf zodra een belexport voor die opdrachtgever, dag en code hem bevat.
- **Verwachte uren**: `uren_verwacht` in `bellers.yaml` voor een dag die nog niet in de urenexport staat (uren x tarief); vervalt vanzelf zodra de urenexport die dag bevat.
- **Peildatum**: de laatste dag in de urenexport, maar niet verder dan de belexports van opdrachtgevers die de laatste 3 weken zijn gebeld (exportdatum uit de bestandsnaam). Alles (resultaten, uren, kosten, opbrengst, targets) telt tot en met die dag. Belexports en belpogingen van later wachten tot de urenexport die dagen ook bevat; het Stuurscherm en `run.py` melden dat.
- **Uren**: `Te betalen` uit de urenexport.
- **Kosten ZZP**: voor een week mét factuur geldt het gefactureerde bedrag. Voor een week zonder factuur is het een schatting: Steam-uren x tarief. Facturen zonder weeknummer gaan naar de week van de factuurdatum (do t/m zo) of naar de week ervoor (ma t/m wo).
- **Kosten eigenaren**: een vaste vergoeding per maand. Die wordt verdeeld over de betaalde uren van die maand.
- **Verdeelsleutel**: Steam splitst uren niet per campagne. De verdeling per dag volgt de belregels; het totaal per beller per opdrachtgever wordt gekalibreerd op de beltijd per campagne uit de contactstatistieken (`verdeelsleutel: steam_gekalibreerd`). Zonder contactstatistieken: alleen belregels.
- **Resultaat uit de memo**: bij `memo_classificatie: true` (Moyee) telt een overdracht (101) met een afspraak of ingeplande tasting in de memo als afspraak (100). Patronen in `instellingen.yaml`; controle op het tabblad Datakwaliteit.
- **Alleen meetbaar werk** (schakelaar, standaard aan): alleen opdrachtgevers met belregels of door Steam gemeten beltijd in de periode.
- **Opbrengst**: wat echt gefactureerd is. Een verkoopfactuur telt verdeeld over de werkdagen (ma t/m vr) van zijn periode (een factuur zonder periode: 28 dagen vanaf de factuurdatum), tot de peildatum. Met `opbrengst_basis: facturen_en_schatting` vult het model werkdagen zonder factuur aan met fee / 20. Overige kosten worden ook over werkdagen verdeeld, zodat een week altijd ma t/m vr is.
- **Werkperiodes**: volgens de verkoopfactuur als die er is ("werkperiode 4, periode ..."), anders vanaf de belstart.
- **Status klant**: `actief`, `pauze` of `gestopt`. Alleen actieve klanten tellen mee in targets en scenario.
- **Overige kosten**: facturen uit `kosten.yaml` (een jaarlicentie wordt per dag verdeeld); maanden zonder factuur krijgen het laatst bekende bedrag als schatting.
- **Indeling dashboard**: zes stappen in vaste volgorde, elk met één vraag en een antwoord in één zin: 1 Samenvatting, 2 Targets, 3 Marge, 4 KPI's per beldag, 5 Bellers, 6 Acties. Daarna Per opdrachtgever (alles van één klant). Stuurscherm en alle detailtabbladen staan onder "Meer details".
- **Belofte per beldag**: `belofte_per_beldag` in klanten.yaml = afgesproken afspraken per beldag van 6 uur. Beldagen per werkperiode = target / belofte (naar boven afgerond); de prijs volgt `staffel_per_beldag` in instellingen.yaml (€ 600 / 575 / 550). Het KPI-plan toont ook wat 25% buffer extra kost. `beldag_uren_nu` corrigeert de meting als beldagen nu korter zijn (OK: 4 uur).
- **Contactstatistieken**: een export met minstens 90% van de pogingen van de vorige totaalstand vervangt die; een kleinere (bv. alleen de laatste week) telt erbij op.
- **KPI's per beldag (stap 4)**: een beldag is `beldag_uren` (6) uur. Per opdrachtgever: target + `target_buffer` (25%) gedeeld door de beldagen die het budget toelaat (fee x (1 - margedoel) min overige kosten, / € 36, / 6 uur). Dat wordt teruggerekend via de gemeten trechter (calls per uur, gesprekken met een beslisser per call, resultaten per gesprek) naar calls, beslissers gesproken en resultaten per beldag. Zonder genoeg eigen data: teamgemiddelde.
- **Beldagen**: een beldag is een dag met minimaal 15 belpogingen voor een opdrachtgever (zonder belpogingen-export: minimaal 1 uur volgens de verdeelsleutel). De betaalde uren van de beller die dag worden verdeeld naar zijn belpogingen per opdrachtgever. Normen per beldag = normen per 4 weken / beldagen per 4 weken. Vast rooster: `beldagen_per_week` in `klanten.yaml`, anders gemeten over de meetperiode.
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
