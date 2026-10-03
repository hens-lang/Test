# LINK. management dashboard

Eén managementomgeving voor LINK. waarin planning, klanten, zzp'ers, facturen en
belresultaten aan elkaar gekoppeld zijn.

Live: https://claude.ai/artifact/Qaea1fo5JpAyaaV42L2X82 (privé; delen via het Share-menu)

## Onderdelen

| Tab | Wat je er doet |
|---|---|
| Overzicht | KPI's (openstaand, gefactureerd, nog te factureren, te betalen zzp'ers, uren, afspraken), wie er vandaag belt, aandachtspunten, grafieken |
| Planning | Weekrooster: per zzp'er per dag inplannen op welk project die belt (met herhalen), diensten bevestigen als gewerkt |
| Projecten | Belcampagnes per klant met tarief, belinstructie, doel per week, uren, warme uitkomsten en marge |
| Klanten | Opdrachtgevers met tarief, betaaltermijn, omzet en openstaand bedrag |
| ZZP'ers | Bellers met uurtarief, volgende dienst, uren, nog te betalen en warme uitkomsten per uur |
| Facturen | Verkoop- en inkoopfacturen, automatisch opgebouwd uit gewerkte uren (+ prijs per afspraak uit de belresultaten) |
| Belresultaten | Upload van de Belstat-belexport (.xls/.csv); zelfde funnel als de weekrapportage |

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

## Opslag

Op claude.ai gebruikt het dashboard een gedeelde database (collecties `klanten`,
`projecten`, `zzp`, `diensten`, `facturen`, `resultaten`). Claude kan die ook lezen en
bijwerken, bijvoorbeeld om na een rapportage de weekcijfers weg te schrijven. Buiten
claude.ai geopend valt het terug op lokale opslag in de browser (label "lokaal").
