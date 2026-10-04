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
    tagline: "Dé partner van B2B-bedrijven.",
    colors: { black: "#000000", blue: "#38b6ff" }
  },

  contact: {
    email: "info@linkgrp.nl",
    phone: "(0172) 27 10 08",
    phoneHref: "+31172271008",
    kvk: "97517267",
    address: { street: "Flemingweg 8", zip: "2408 AV", city: "Alphen aan den Rijn" },
    linkedin: "https://nl.linkedin.com/in/hens-boer-359b8a294",
    // Link naar je online agenda (bijv. Google Agenda-afspraakplanning of Calendly).
    // Ingevuld: alle "Plan een kennismaking"-knoppen openen je agenda.
    // Leeg: de knoppen gaan naar het formulier op de contactpagina.
    bookingUrl: "https://calendar.app.google/DDuUgvNtDmocqqBZ9",
    web: "www.linkgrp.nl",
    // Reactietijd: komt terug in de zwevende chip, contactpagina en waarden.
    responseTime: "3 minuten",
    responseShort: "3 min",
    // Partnerportaal (leads, afspraken, updates). Vul de echte URL in;
    // zolang dit leeg is, verbergt de site de portaal-knop.
    portalUrl: "https://admin.linkgrp.nl",
    form: {
      // Web3Forms: berichten uit het contactformulier komen per e-mail binnen
      // op het adres dat bij Web3Forms aan deze sleutel hangt.
      endpoint: "https://api.web3forms.com/submit",
      web3formsKey: "38064945-fdcb-40a5-b0a3-8aaab660ecc6",
      subject: "Nieuwe aanvraag via linkgrp.nl",
      fromName: "LINK. website"
    }
  },

  // Apollo website-tracking: laadt alleen na toestemming via de cookiemelding.
  // Leeg laten = geen tracking en geen cookiemelding.
  tracking: { apolloAppId: "695040eaae2147001516e8ad" },

  // Extra links in de footer (niet in het hoofdmenu).
  navFooter: [],

  nav: [
    { href: "diensten.html", label: "Diensten" },
    { href: "over-link.html", label: "Over LINK." },
    { href: "verhalen.html", label: "Verhalen" },
    { href: "werken-bij.html", label: "Werken bij" },
    { href: "contact.html", label: "Contact" }
  ],

  // Oprichter. LINK. wordt geleid door Hens Boer.
  founder: {
    name: "Hens Boer",
    firstName: "Hens",
    role: "Oprichter LINK.",
    quote: "Ik heb jarenlang ervaring in direct sales. Elke dag in gesprek met mensen die mij niet verwachtten, over een product waar ze niet op zaten te wachten. Je leert snel wat werkt en wat niet. Die ervaring zet ik nu in voor onze partners."
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
    typen:   { src: "assets/img/hens/hens-typen", widths: [800, 1400], alt: "Hens Boer werkt in het partnerportaal op zijn laptop" }
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
      text: "We gaan de markt in met koude acquisitie, persoonlijk aan de telefoon en met jouw verhaal. We plannen afspraken met beslissers en scherpen onderweg doelgroep en propositie aan.",
      gets: ["Koude acquisitie door ons team", "Afspraken met beslissers", "Aanscherpen op wat we horen", "Elke week een update"]
    },
    {
      name: "Eerste meetings",
      text: "Jij zit aan tafel bij gekwalificeerde prospects. Wij sturen bij op basis van wat werkt.",
      gets: ["Afspraken in jouw agenda", "Leads met de context van het gesprek"]
    },
    {
      name: "Structurele stroom",
      text: "Na de pilot bouwen we door naar een vaste stroom gekwalificeerde prospects. Week na week.",
      gets: ["Voorspelbare groei", "Eén vast aanspreekpunt"]
    }
  ],

  // Feitenstrook onder "Zo werkt het". {response} = contact.responseTime.
  facts: [
    { n: "1", l: "vast aanspreekpunt" },
    { n: "100%", l: "persoonlijk" },
    { n: "52×", l: "per jaar een update" }
  ],

  // Voor beslissers: wat eigenaren en salesverantwoordelijken belangrijk vinden.
  audiences: [
    {
      id: "eigenaar",
      label: "Ik ben eigenaar",
      title: "Groei, zonder dat jij zelf de telefoon pakt.",
      points: [
        { h: "Een werkmethode uit de praktijk", p: "Van kick-off tot een structurele stroom nieuwe klanten. Elke week aangescherpt op basis van data uit onze gesprekken." },
        { h: "Een gerichte start", p: "Je start met een pilot: we bellen, plannen afspraken en scherpen onderweg aan. Zo bouwen we vanaf dag één aan nieuwe klanten." },
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

  // Markten waar LINK. thuis is, afgeleid van de huidige partners (zonder namen).
  sectors: [
    "Installatie- & elektrotechniek",
    "Maakindustrie",
    "Software, SaaS & AI",
    "Cybersecurity",
    "Zakelijke dienstverlening",
    "Marketing & creatief",
    "Facilitair & hygiëne",
    "Duurzaamheidscertificering",
    "Groothandel & logistiek"
  ],

  // Anonieme referenties: alleen functie + type bedrijf, nooit een bedrijfsnaam.
  // Alleen echte uitspraken van partners, met hun toestemming.
  // Leeg = het blok verschijnt niet op de site.
  // Voorbeeld: { quote: "…", role: "Directeur", company: "IT-bedrijf" }
  references: [],

  // Vacatures. Zet open: false om een vacature tijdelijk te verbergen.
  // "google": true geeft de vacature mee aan Google Jobs (niet voor open sollicitatie).
  jobs: [
    {
      id: "acquisitiespecialist",
      title: "Acquisitiespecialist",
      hours: "Fulltime of parttime",
      place: "Alphen aan den Rijn",
      open: true, google: true, posted: "2026-09-28",
      intro: "Je voert namens onze partners gesprekken met beslissers en zorgt dat zij aan tafel komen bij de bedrijven die ze als klant willen hebben.",
      does: [
        "Je belt persoonlijk met directeuren en eigenaren van B2B-bedrijven",
        "Je plant kennismakingen en afspraken voor onze partners",
        "Je denkt mee over doelgroep en propositie, op basis van wat je hoort",
        "Je legt je gesprekken vast, zodat we samen elke week scherper worden"
      ],
      you: [
        "Je bent communicatief sterk en vindt het leuk om met mensen te praten",
        "Je hoort een nee, en gaat gewoon door",
        "Je bent nieuwsgierig naar hoe bedrijven werken en wat ze drijft",
        "Ervaring in sales is mooi, maar mentaliteit is belangrijker"
      ],
      gets: [
        "Een plek in een klein en hecht team, met directe lijnen naar de oprichter",
        "Veel ruimte om te leren, en begeleiding vanaf dag één",
        "Werken met data en onze eigen AI-modellen",
        "Een passend salaris, dat bespreken we graag persoonlijk"
      ]
    },
    {
      id: "stage",
      title: "Commerciële stage of bijbaan",
      hours: "Parttime, naast je studie",
      place: "Alphen aan den Rijn",
      open: true, google: true, posted: "2026-09-28",
      intro: "Ben je student en wil je leren hoe B2B-acquisitie echt werkt? Dan leer je het bij ons in de praktijk.",
      does: [
        "Je voert zelf gesprekken met beslissers, met begeleiding",
        "Je helpt bij het voorbereiden van doelgroepen en prospectlijsten",
        "Je leert werken met data om gesprekken steeds beter te maken"
      ],
      you: [
        "Je studeert, bijvoorbeeld in commerciële economie, marketing of bedrijfskunde",
        "Je durft de telefoon te pakken en vindt het leuk om te leren",
        "Je bent een paar dagen per week beschikbaar"
      ],
      gets: [
        "Echte praktijkervaring die je nergens anders zo snel opdoet",
        "Persoonlijke begeleiding van de oprichter",
        "Een passende stage- of bijbaanvergoeding, die bespreken we persoonlijk"
      ]
    },
    {
      id: "open",
      title: "Open sollicitatie",
      hours: "Fulltime of parttime",
      place: "Alphen aan den Rijn",
      open: true, google: false,
      intro: "Staat jouw functie er niet tussen, maar wil je wel bij LINK. werken? Vertel ons wie je bent en wat je zoekt.",
      does: [], you: [], gets: []
    }
  ],

  // Veelgestelde vragen van beslissers. Voedt ook de FAQ-structured data voor Google.
  // {response} = contact.responseTime.
  faq: [
    { q: "Wie belt er namens ons?",
      a: "Ons eigen, kleine team. Geen callcenter en geen doorverkochte uren. We bellen onder jouw naam en met jouw verhaal, voorbereid op jouw markt en doelgroep. Voor de beslisser aan de lijn spreekt hij gewoon met jouw bedrijf." },
    { q: "Wat als we al een salesteam hebben?",
      a: "Dan zorgen wij dat hun agenda gevuld raakt. Wij voeren de eerste gesprekken met beslissers en plannen de afspraak. Jouw team doet daarna waar het goed in is: verkopen." },
    { q: "Hoe bepalen jullie wie onze ideale klant is?",
      a: "Samen, tijdens de kick-off. We kijken naar je beste klanten, je propositie en je groeidoel. Daarna sturen we bij op basis van wat we in de gesprekken horen, tot we precies bij de juiste bedrijven zitten." },
    { q: "Hoe snel zien we resultaat?",
      a: "Een pilot is bij ons geen proef om te kijken of het werkt. Het is een volwaardige start: we doen koude acquisitie, plannen afspraken met beslissers en scherpen onderweg samen je propositie aan. Staat die scherp, dan weten we dat het werkt met onze manier van bellen. Je hoort elke week waar we staan, en in de kennismaking geven we je een concreet beeld voor jouw markt." },
    { q: "Wat kost het?",
      a: "Dat hangt af van je doelgroep en je ambitie. In de kennismaking maken we het concreet. Je start altijd met een pilot, waarin we direct bellen, afspraken plannen en de basis leggen voor een structurele stroom nieuwe klanten." },
    { q: "Hoe houden we zicht op de voortgang?",
      a: "Via je eigen partnerportaal, met alle leads, afspraken en updates op één plek. Elke week een update, en heb je een vraag, dan heb je binnen {response} een reactie." },
    { q: "Voor welke bedrijven werken jullie?",
      a: "Voor B2B-bedrijven met een sterk product of een sterke dienst die structureel aan tafel willen bij nieuwe klanten. Past het niet, dan zeggen we dat eerlijk. Liever een eerlijk nee vooraf dan een moeizame samenwerking achteraf." }
  ],

  // Nagebouwd partnerportaal (illustratie met voorbeeldregels, geen echte klantdata).
  portalMock: {
    menu: ["Dashboard", "Afspraken & leads", "Rapportages", "Kalender", "Logboek"],
    active: "Logboek",
    // Illustratief: statuswijzigingen zoals het logboek ze toont.
    entries: [
      { who: "LINK.", kind: "Afspraak", from: "Afspraak ingepland", to: "Deal gewonnen", when: "25 sep. 12:44", win: true },
      { who: "LINK.", kind: "Afspraak", from: "Vervolg gepland", to: "Offerte gestuurd", when: "24 sep. 16:10" },
      { who: "LINK.", kind: "Lead", from: "Lead", to: "Afspraak ingepland", when: "23 sep. 09:32" }
    ]
  },


  // Voorbeelden voor de kaart in de hero (illustratief, geen echte partners).
  liveCard: [
    ["Kennismaking ingepland", "Installatietechniek", "Beslisser", "Directeur-eigenaar"],
    ["Afspraak ingepland", "Zakelijke dienstverlening", "Beslisser", "Commercieel directeur"],
    ["Kennismaking ingepland", "Maakindustrie · 50-100 medewerkers", "Beslisser", "Operationeel directeur"],
    ["Afspraak ingepland", "IT-dienstverlener · 25-50 medewerkers", "Beslisser", "Algemeen directeur"]
  ]
};
