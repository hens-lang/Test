/*
 * LINK. | centrale databron van linkgrp.nl
 *
 * Eén bestand, één waarheid. Navigatie, contactgegevens, oprichter, foto's,
 * formulier en werkmethode worden allemaal hieruit gelezen.
 * Pas je hier iets aan (telefoonnummer, portaal-URL, foto), dan klopt het
 * op elke pagina tegelijk.
 *
 * Bronnen:
 *  - Drive > Website > "Huisstijl"            (zwart #000000, blauw #38b6ff, Open Sans)
 *  - Drive > Website > "Website Teksten Opzet" (alle copy)
 *  - Drive > Website > "LINK. LOGO's.zip"      (assets/img/logo-*.png)
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
    // Reactietijd: komt terug in de zwevende chip, contactpagina en waarden.
    responseTime: "3 minuten",
    responseShort: "3 min",
    // Partnerportaal (leads, afspraken, updates). Vul de echte URL in;
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
    quote: "Drie jaar lang heb ik dagelijks deuren aangebeld en mensen gebeld die mij niet verwachten, met een product waar zij niet op zitten te wachten. Je leert snel wat werkt en wat niet. Deze ervaring zet ik nu in voor onze partners."
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
    portaal: { src: "assets/img/hens/hens-portaal", widths: [800, 1400], alt: "Het LINK. partnerportaal op een laptop" }
  },

  // Zo werkt het. Helder over wat je per fase krijgt, bewust niet over
  // hoe we het intern doen: dat laten we zien in een kennismaking.
  // pilotLabel: vul bijv. "8 weken" in zodra de pilotduur vaststaat.
  pilotLabel: "",
  method: [
    {
      name: "Kick-off",
      text: "We leren jouw bedrijf, propositie en markt kennen. Samen bepalen we het ideale klantprofiel en wat succes voor jou is.",
      gets: ["Een scherp ideaal klantprofiel", "Heldere afspraken over succes"]
    },
    {
      name: "Pilot",
      text: "We gaan de markt in, persoonlijk aan de telefoon en met jouw verhaal. Wat we horen, vertalen we naar scherpere keuzes in doelgroep en propositie.",
      gets: ["Gesprekken met beslissers", "Marktinzichten en business development", "Elke week een update"]
    },
    {
      name: "Eerste meetings",
      text: "Jij zit aan tafel bij gekwalificeerde prospects. Wij sturen bij op basis van wat werkt.",
      gets: ["Afspraken in jouw agenda", "Leads met de context van het gesprek"]
    },
    {
      name: "Structurele stroom",
      text: "Na de pilot bouwen we door naar een vaste stroom gekwalificeerde prospects. Zonder lange contracten.",
      gets: ["Voorspelbare groei", "Eén vast aanspreekpunt"]
    }
  ],

  // Feitenstrook onder "Zo werkt het". {response} = contact.responseTime.
  facts: [
    { n: "1", l: "vast aanspreekpunt" },
    { n: "100%", l: "persoonlijk" },
    { n: "{responseShort}", l: "reactietijd" },
    { n: "52×", l: "per jaar een update" }
  ],

  // Voor beslissers: wat eigenaren en salesverantwoordelijken belangrijk vinden.
  audiences: [
    {
      id: "eigenaar",
      label: "Ik ben eigenaar",
      title: "Groei, zonder dat jij zelf de telefoon pakt.",
      points: [
        { h: "Bewezen werkmethode", p: "Van kick-off tot een structurele stroom nieuwe klanten. Getest in de praktijk, niet op papier." },
        { h: "Laag risico", p: "Je start met een pilot en zit nergens lang aan vast. Wij verdienen onze plek elke maand opnieuw." },
        { h: "Voorspelbare instroom", p: "Week na week gesprekken met bedrijven die jij als klant wilt hebben." },
        { h: "Korte lijnen", p: "Eén vast aanspreekpunt in een klein en hecht team. Je hebt binnen {response} een reactie." }
      ]
    },
    {
      id: "sales",
      label: "Ik ben salesverantwoordelijk",
      title: "Een gevulde agenda met de juiste beslissers.",
      points: [
        { h: "Gekwalificeerde gesprekken", p: "Geen koude namen, maar beslissers die passen bij jouw ideale klantprofiel." },
        { h: "Grip en inzicht", p: "Leads, afspraken en updates in je partnerportaal. Elke week weet je waar je staat." },
        { h: "Scherpere propositie", p: "Wat we in de markt horen, vertalen we naar concrete verbeterpunten voor jouw pitch." },
        { h: "Snel bijsturen", p: "Werkt iets niet? Dan schakelen we direct door, en zeggen we het eerlijk." }
      ]
    }
  ],

  // Voorbeelden voor de kaart in de hero (illustratief, geen echte partners).
  liveCard: [
    ["Kennismaking ingepland", "Installatietechniek", "Beslisser", "Directeur-eigenaar"],
    ["Afspraak ingepland", "Zakelijke dienstverlening", "Beslisser", "Commercieel directeur"],
    ["Kennismaking ingepland", "Maakindustrie · 50-100 medewerkers", "Beslisser", "Operationeel directeur"],
    ["Afspraak ingepland", "IT-dienstverlener · 25-50 medewerkers", "Beslisser", "Algemeen directeur"]
  ]
};
