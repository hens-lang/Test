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

  // Het traject met een partner. Bewust alleen de mijlpalen: hoe we het
  // doen, laten we zien in een kennismaking, niet op de website.
  method: [
    { name: "Kick-off", text: "Jouw bedrijf, jouw markt en jouw groeidoel. Scherp op tafel." },
    { name: "Eerste belmoment", text: "Jouw verhaal voor het eerst in de markt. Persoonlijk en goed voorbereid." },
    { name: "Eerste meeting", text: "Jij aan tafel bij een gekwalificeerde prospect." },
    { name: "Structurele stroom", text: "Een vaste stroom gekwalificeerde prospects. Week na week." }
  ],

  // Voorbeelden voor de kaart in de hero (illustratief, geen echte partners).
  liveCard: [
    ["Kennismaking ingepland", "Installatietechniek", "Beslisser", "Directeur-eigenaar"],
    ["Warme lead overgedragen", "Zakelijke dienstverlening", "Moment", "Na de zomer"],
    ["Kennismaking ingepland", "Maakindustrie · 50-100 medewerkers", "Beslisser", "Operationeel directeur"],
    ["Terugbelafspraak", "Horeca & kantoren", "Reden", "Contract loopt af in Q1"]
  ]
};
