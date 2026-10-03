# LINK. management dashboard

Eén managementomgeving voor LINK. waarin planning, klanten, zzp'ers, facturen en
belresultaten aan elkaar gekoppeld zijn.

Live: https://claude.ai/artifact/Qaea1fo5JpAyaaV42L2X82 (privé; delen via het Share-menu)

## Onderdelen

| Tab | Wat je er ziet |
|---|---|
| Overzicht | Per opdrachtgever de lopende werkperiode met stoplicht: resultaat tegenover target, prognose, wat er nog nodig is (per werkdag), ingeplande beluren, factuurstand en contractafspraak. Daaronder "Vandaag doen", factuurmails van de laatste 14 dagen en de laatste Twinfield-stand |
| Dagstart | Briefing per beller voor vandaag: blokken met opdrachtgever, doel, stand van de werkperiode, pitch, beste beltijd, focus en wat werkt (uit de laatste rapportage), open terugbelafspraken en feedback op de gesprekken (cijfers laatste 4 weken tegen het team, norm 1 resultaat per blok van 3 uur, plus notities van Hens). Met een knop om de briefing te kopiëren voor WhatsApp. Daaronder wat er deze week nodig is om de werkperiodes te halen, per opdrachtgever in één regel; klik voor de verdeling over bellers. Plus briefing per beller en notities |
| Planning | Weekrooster: per beller per dag op welke opdrachtgever die belt |
| Facturen | Verkoop- en inkoopfacturen |
| Beheer | Opdrachtgevers, bellers, belexports uploaden en klantgegevens |

Gestopte en gepauzeerde opdrachtgevers zijn verborgen (niet verwijderd); "Toon alles" in Beheer laat ze weer zien.
Pilots die nog niet gestart zijn staan onderaan.

## Hoe alles samenhangt

```
klanten ──< projecten ──< diensten >── zzp
                │             │
                │             ├─ factuurVerkoopId → facturen (verkoop, per klant)
                │             └─ factuurInkoopId  → facturen (inkoop, per zzp'er)
                └──< resultaten (per week) ── perAgent → zzp
```

- Een **dienst** (planning) koppelt een zzp'er aan een project op een datum. Staat hij op
  *gewerkt*, dan telt hij mee voor uren, marge en facturen.
- Een **factuur** pakt alle gewerkte, nog niet gefactureerde diensten in een periode en
  zet het factuur-id op die diensten, zodat niets dubbel gefactureerd wordt. Verwijder je
  de factuur, dan worden de uren weer factureerbaar.
- **Belresultaten** gebruiken dezelfde telling als `funnel.py` uit de rapportage-pijplijn
  (dedupliceren op Bedrijf; gesproken = 100/101/200/201/202/500; warm = 100/101/500).
  De klant wordt herkend via de Campagne-kolom of de Belstat-naam van het project; lukt
  dat niet, dan vraagt het dashboard het je (nooit gokken op doelgroep). Per beller worden
  de cijfers gekoppeld aan de zzp'er met dezelfde naam als "Naam agent".
- Bij elk weekresultaat staat de bijbehorende bestandsnaam van de rapportage
  (`Rapportage <Klant> wk <nr>.pdf`), dezelfde naam waar de Drive-workflow op matcht.

## Vaste regels

- **Werkperiode**: telt vanaf de belstart in blokken van 4 weken (pilots 12 weken). Target = doel per week x weken.
- **Stoplicht**: prognose = gehaald / verstreken werkdagen x werkdagen in de periode. Groen >= target, oranje 80-100%, rood < 80%.
- **Nodig deze week** = wat nog ontbreekt in de periode, naar rato van de werkdagen die deze week nog in de periode vallen.
- **Inkoopfacturen van zzp'ers** worden binnen 14 dagen betaald. Na de vervaldatum (factuurdatum + 14) staan ze automatisch op betaald.
- **Twinfield**: Hens stuurt dagelijks een screenshot van de factuurstatussen; Claude zet de statussen gelijk en legt de totalen vast in `sync/twinfield`. Het overzicht laat zien of dashboard en Twinfield aansluiten.
- **Mail**: het dashboard leest (alleen lezen) Gmail op factuurmails van de laatste 14 dagen: verstuurde facturen, binnenkomende facturen van bellers en doorsturingen naar Basecone. Het maakt nooit concepten aan; per mail is er hooguit een knop om de factuur in het dashboard bij te werken.

- **Beste beltijd** per opdrachtgever: resultaten (volgens wat er voor die klant telt) per 100 belpogingen, per blok van 2 uur (9-11, 11-13, 13-15, 15-17) en per weekdag, uit de Steam-belpogingen en belexports. Minder dan 500 pogingen in totaal = indicatief; een blok onder 150 pogingen staat gemarkeerd.
- **Werkperiodes**: bij elke opdrachtgever staat de historie per periode (resultaat tegenover target, afspraken, leads, pogingen) en de Steam-stand van de laatste export. Bij Moyee gelden aparte targets per code (4 afspraken, 10 leads per 4 weken).

## Rekenwijze dagstart

- Tempo = (afspraken + overdrachten) per gewerkt beluur over de laatste 8 weken met belexport en uren. Zonder historie: het veld "Verwacht per beluur" bij het project.
- Het resterende weekdoel wordt verdeeld naar verwachte bijdrage: ingeplande uren x eigen tempo van de beller (anders het projecttempo).
- Tekort = resterend - (ingeplande uren x tempo); extra beluren = tekort / tempo.
- Op zaterdag/zondag toont de dagstart de eerstvolgende maandag.

## Opslag

Op claude.ai gebruikt het dashboard een gedeelde database (collecties `klanten`,
`projecten`, `zzp`, `diensten`, `facturen`, `resultaten`, `dagstart`, `sync`). Claude kan die ook lezen en
bijwerken, bijvoorbeeld om na een rapportage de weekcijfers weg te schrijven. Buiten
claude.ai geopend valt het terug op lokale opslag in de browser (label "lokaal").

## Bronnen van de huidige data (3 okt 2026)

- Opdrachtgevers, fees, targets, belstart, bellers en tarieven, verkoop- en bellerfacturen, uren per beller per dag en belresultaten: het belprestatie-dashboard (Steam-exports, afgestemd op Twinfield, peildatum 2 okt).
- Contactpersonen, adressen, contractafspraken: Gmail en Google Drive.
- Geplande diensten na 2 okt: agenda "LINK. ZZP" (nog zonder opdrachtgever; in te delen via de dagstart).
- Factuurstatussen: Twinfield-screenshot 3 okt.
