# Sinterklaas Lootjes 🎁

Eerlijk lootjes trekken voor Sinterklaasgedichten met de familie. Niemand ziet wie wie heeft getrokken — ook de organisator niet.

## Hoe werkt het?

1. **Organisator** opent `index.html` en vult in:
   - het feest (naam, datum, budget, wanneer het gedicht klaar moet zijn);
   - de deelnemers. Per persoon kun je optioneel invullen:
     - **Huishouden** – mensen met hetzelfde huishouden trekken elkaar niet (bijv. partners);
     - **Niet trekken** – namen die iemand niet mag krijgen (bijv. wie diegene vorig jaar had);
     - **Tips** – hobby's, grappige gewoontes of wensen. Die ziet alleen degene die deze persoon trekt.
2. Klik op **Trek de lootjes**. Je krijgt per persoon een geheime link, die je met één klik via WhatsApp verstuurt.
3. **Iedereen** opent de eigen link, klikt op *Open mijn lootje* en ziet voor wie hij/zij een gedicht maakt,
   met de tips, het budget, de deadline en een opzetje + rijmwoorden voor het gedicht.

De deelnemerslijst wordt in de browser van de organisator bewaard, zodat je volgend jaar snel opnieuw kunt trekken.
De uitslag wordt nergens opgeslagen: die zit alleen (versleuteld) in de persoonlijke links.
Trek je opnieuw, stuur dan iedereen de nieuwe link.

## Online zetten

**Live:** https://hens-lang.github.io/Test/sinterklaas-lootjes/ (gepubliceerd via de `gh-pages`-branch).

De links werken alleen als de pagina online staat. Makkelijkste manier: zet GitHub Pages aan voor deze repository
(Settings → Pages → branch kiezen) en open `…/sinterklaas-lootjes/index.html`.

Open je het bestand alleen lokaal? Gebruik dan de knop **Alleen code**: stuur iedereen het bestand plus hun code,
en laat ze de code plakken bij *Heb je een code gekregen?*.

## Bestanden

| Bestand       | Wat                                                                           |
|---------------|-------------------------------------------------------------------------------|
| `index.html`  | De app: organisator-scherm én lootje-scherm.                                  |
| `lootjes.js`  | Gedeelde logica: regels controleren, eerlijk trekken, codes maken en lezen.   |
| `test.js`     | Tests voor `lootjes.js` (`node test.js`).                                      |

> De codes zijn versluierd zodat niemand per ongeluk een naam in de link leest; het is geen echte beveiliging.
