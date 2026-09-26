/*
 * LINK. | centrale databron van linkgrp.nl
 *
 * Eén bestand, één waarheid. Navigatie, contactgegevens, team, formulier,
 * resultaatcodes en de voorbeeldrapportage worden allemaal hieruit gelezen.
 * Pas je hier iets aan (telefoonnummer, portaal-URL, foto), dan klopt het
 * op elke pagina tegelijk.
 *
 * Bronnen:
 *  - Drive > Website > "Huisstijl"            (zwart #000000, blauw #38b6ff, Open Sans)
 *  - Drive > Website > "Website Teksten Opzet" (alle copy)
 *  - Drive > Website > "LINK. LOGO's.zip"      (assets/img/logo-*.png)
 *  - Rapportage-pijplijn (funnel.py)           (resultaatcodes + funnel-definities)
 */
window.LINK = {
  brand: {
    name: "LINK.",
    tagline: "Dè partner van B2B bedrijven.",
    colors: { black: "#000000", blue: "#38b6ff" }
  },

  contact: {
    email: "info@linkgrp.nl",
    phone: "(0172) 27 10 08",
    phoneHref: "+31172271008",
    web: "www.linkgrp.nl",
    region: "Zuid-Holland & Noord-Holland",
    // Klantportaal (leads, afspraken, rapportages). Vul de echte URL in;
    // zolang dit leeg is, verbergt de site de portaal-knop.
    portalUrl: "",
    form: {
      // Optioneel: koppel een Google Form. Vul de formResponse-URL en de
      // entry-ID's in. Leeg = het formulier opent een e-mail naar info@.
      endpoint: "",
      fields: {
        naam: "",
        bedrijf: "",
        email: "",
        telefoon: "",
        tafel: "",
        ambitie: ""
      }
    }
  },

  nav: [
    { href: "index.html", label: "Home" },
    { href: "diensten.html", label: "Diensten" },
    { href: "ons-verhaal.html", label: "Ons verhaal" },
    { href: "waarom-link.html", label: "Waarom LINK." },
    { href: "contact.html", label: "Contact" }
  ],

  // Oprichter. LINK. wordt geleid door Hens Boer.
  founder: {
    name: "Hens Boer",
    firstName: "Hens",
    role: "Oprichter LINK.",
    quote: "Drie jaar lang heb ik dagelijks deuren aangebeld en mensen gebeld die mij niet verwachten, met een product waar zij niet op zitten te wachten. Je leert snel wat werkt en wat niet. Deze ervaring zet ik nu in voor onze opdrachtgevers."
  },

  // Alle foto's van de site. Elke pagina verwijst naar een sleutel
  // (bijv. data-photo="haven"); de site bouwt zelf de juiste formaten.
  // Bestanden staan in assets/img/hens/ als <src>-<breedte>.jpg.
  // Laat src leeg ("") en het fotovak verdwijnt netjes van de pagina.
  photos: {
    hero:    { src: "assets/img/hens/hens-hero", widths: [600, 1000, 1400], alt: "Hens Boer van LINK. aan de telefoon" },
    bellen:  { src: "assets/img/hens/hens-bellen", widths: [600, 1000], alt: "Hens Boer belt lachend in de haven" },
    held:    { src: "assets/img/hens/hens-held", widths: [600, 1000], alt: "Hens Boer, oprichter van LINK." },
    portret: { src: "assets/img/hens/hens-portret", widths: [600, 1000], alt: "Portret van Hens Boer" },
    waarom:  { src: "assets/img/hens/hens-waarom", widths: [600, 1000], alt: "Hens Boer kijkt in de camera" },
    bedrijf: { src: "assets/img/hens/hens-bedrijf", widths: [900, 1600, 2200], alt: "Hens Boer op een bedrijventerrein" },
    notitie: { src: "assets/img/hens/hens-notitie", widths: [600, 1000], alt: "Hens Boer maakt aantekeningen in zijn notitieboek" },
    avatar:  { src: "assets/img/hens/hens-avatar", widths: [160, 320], alt: "Hens Boer" },
    koffie:  { src: "assets/img/hens/hens-koffie", widths: [600, 1000], alt: "Hens Boer drinkt koffie uit een blauw kopje" },
    // Namen, notities, URL en bladwijzers op het scherm zijn onleesbaar gemaakt (AVG).
    portaal: { src: "assets/img/hens/hens-portaal", widths: [800, 1400], alt: "Het LINK. klantportaal op een laptop" }
  },

  steps: [
    "We verdiepen ons in het bedrijf van onze opdrachtgever.",
    "We bepalen samen het groeidoel.",
    "We bepalen samen een doelgroep.",
    "We stellen een prospectlijst samen.",
    "De juiste beslisser bereiken via persoonlijke en gerichte outreach.",
    "Interesse polsen en kansen kwalificeren.",
    "De afspraak inplannen. Daarna is het aan jou."
  ],

  // Identiek aan de rapportage-pijplijn (funnel.py). Wat een prospect hier
  // ziet, is precies wat een opdrachtgever elke week in zijn rapportage leest.
  resultCodes: [
    { code: 100, label: "Afspraak", group: "warm" },
    { code: 101, label: "Overdracht", group: "warm" },
    { code: 500, label: "Terugbelafspraak", group: "warm" },
    { code: 200, label: "Geen interesse", group: "gesproken" },
    { code: 201, label: "Al voorzien", group: "gesproken" },
    { code: 202, label: "Niet passend", group: "gesproken" },
    { code: 501, label: "Informatiemail", group: "vervolg" },
    { code: 502, label: "Terugbelverzoek", group: "vervolg" },
    { code: 300, label: "Onjuist nummer", group: "onbereikt" },
    { code: 400, label: "Geen gehoor", group: "onbereikt" },
    { code: 401, label: "Voicemail", group: "onbereikt" },
    { code: 402, label: "Bezet", group: "onbereikt" }
  ],

  funnel: {
    warm: [100, 101, 500],
    spoken: [100, 101, 200, 201, 202, 500]
  },

  // Voorbeeldweek (fictief) om het rapportageformat te laten zien.
  // Per code: aantal belregels en aantal unieke bedrijven. De site bouwt
  // hier losse belregels van en rekent ze door met dezelfde funnel-logica.
  demoWeek: {
    label: "Voorbeeldweek",
    week: 38,
    rows: [
      { code: 400, rows: 150, companies: 112 },
      { code: 401, rows: 60, companies: 51 },
      { code: 402, rows: 12, companies: 12 },
      { code: 300, rows: 20, companies: 20 },
      { code: 200, rows: 70, companies: 68 },
      { code: 201, rows: 30, companies: 30 },
      { code: 202, rows: 18, companies: 18 },
      { code: 500, rows: 14, companies: 14 },
      { code: 501, rows: 20, companies: 20 },
      { code: 502, rows: 8, companies: 8 },
      { code: 101, rows: 4, companies: 4 },
      { code: 100, rows: 6, companies: 6 }
    ]
  }
};
