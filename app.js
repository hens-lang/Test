/* ============================================================
   Vangst — app prototype logica
   Klikbare navigatie tussen schermen + dummy-gesprekken.
   Alle data is verzonnen (Schildersbedrijf Van Dijk, Gouda).
   ============================================================ */

/* ---- Navigatie tussen hoofdschermen ---- */
const schermen = ['onboarding', 'dashboard', 'inbox', 'gesprek', 'afspraken', 'opvolging', 'instellingen'];
// Schermen met onderbalk zichtbaar + bijbehorend nav-tabblad
const navSchermen = ['dashboard', 'inbox', 'afspraken', 'opvolging', 'instellingen'];

function gaNaar(naam) {
  schermen.forEach(s => {
    const el = document.getElementById('scherm-' + s);
    if (el) el.classList.toggle('actief', s === naam);
  });

  // Onderbalk tonen/verbergen
  const nav = document.getElementById('nav');
  nav.classList.toggle('verborgen', !navSchermen.includes(naam));

  // Actief tabblad markeren
  document.querySelectorAll('.nav button').forEach(b => {
    b.classList.toggle('actief', b.dataset.nav === naam);
  });

  // Naar boven scrollen binnen het scherm
  const actief = document.getElementById('scherm-' + naam);
  if (actief) actief.scrollTop = 0;
}

/* ---- Onboarding ---- */
function obNaar(stap) {
  document.querySelectorAll('[data-ob]').forEach(el => {
    el.style.display = (Number(el.dataset.ob) === stap) ? 'flex' : 'none';
    el.style.flexDirection = 'column';
    el.style.flex = '1';
  });
  document.querySelectorAll('[data-ob-stap]').forEach(el => {
    el.classList.toggle('aan', Number(el.dataset.obStap) <= stap);
  });
  document.getElementById('scherm-onboarding').scrollTop = 0;
}

// Branchekeuze
document.getElementById('branche-grid').addEventListener('click', e => {
  const knop = e.target.closest('.branche');
  if (!knop) return;
  document.querySelectorAll('#branche-grid .branche').forEach(b => b.classList.remove('gekozen'));
  knop.classList.add('gekozen');
});

// Kanaal koppelen (mock)
function koppel(knop, melding) {
  knop.classList.add('gekoppeld');
  knop.querySelector('.k-status').textContent = '✓';
  toon(melding);
}

/* ---- Gesprekken (dummy-data) ---- */
const gesprekken = {
  debruin: {
    naam: 'Mevr. De Bruin', avatar: 'MB', kanaalIcoon: '💬', kanaal: 'via WhatsApp',
    berichten: [
      { van: 'klant', tekst: 'Hoi, ik zoek iemand om onze kozijnen buiten te schilderen, ongeveer 8 ramen. Kan je langskomen voor een prijs?', tijd: '09:12' },
      { van: 'ai', tekst: 'Goeiemorgen! Zeker, dat doen we regelmatig. 8 kozijnen buiten is prima te doen. Ik kom graag even kijken voor een nette prijs. 👍', tijd: '09:12' },
      { van: 'ai', tekst: 'Schikt donderdag rond 15:00 in Gouda? Dan meet ik alles op en heb je snel een offerte.', tijd: '09:12' },
      { van: 'klant', tekst: 'Donderdag is top, tot dan!', tijd: '09:15' },
    ],
    voorstel: "Genoteerd, ik zet 'm in de agenda. Tot donderdag! 🎨",
  },
  smit: {
    naam: 'Peter Smit', avatar: 'PS', kanaalIcoon: '💬', kanaal: 'via WhatsApp',
    berichten: [
      { van: 'klant', tekst: 'Goedemiddag, we hebben houtrot bij de dakkapel. Kan er iemand komen kijken?', tijd: '10:44' },
      { van: 'ai', tekst: 'Hallo Peter! Houtrot pakken we vaak aan, geen zorgen. Ik plan even iemand in om te kijken hoe erg het is.', tijd: '10:45' },
      { van: 'ai', tekst: 'Kan het vandaag om 14:00 uitkomen? Dan zijn we toch in de buurt.', tijd: '10:45' },
      { van: 'klant', tekst: 'Top, dan hoor ik het graag. Bedankt alvast!', tijd: '11:02' },
    ],
    voorstel: 'Helemaal goed, tot vanmiddag 14:00 dan! We bellen even aan. 👋',
  },
  bakker: {
    naam: 'Jeroen Bakker', avatar: 'JB', kanaalIcoon: '🌐', kanaal: 'via websiteformulier',
    berichten: [
      { van: 'klant', tekst: 'Via de website: graag een offerte voor het sausen van de woonkamer en hal.', tijd: 'ma 09:30' },
      { van: 'ai', tekst: 'Dag Jeroen, bedankt voor je aanvraag! Woonkamer en hal sausen doen we zo gepiept. Ik stuur je een offerte toe.', tijd: 'ma 09:31' },
      { van: 'ai', tekst: 'Je offerte staat in de mail: €780 inclusief materiaal. Laat je even weten of het je aanstaat?', tijd: 'ma 09:40' },
      { van: 'ai', tekst: 'Hoi Jeroen, even een vriendelijk seintje over de offerte van vorige week. Zullen we een datum prikken?', tijd: 'gisteren' },
      { van: 'klant', tekst: 'Ik laat het je deze week weten, druk momentje', tijd: 'gisteren' },
    ],
    voorstel: 'Helemaal begrijpelijk, geen haast! Ik hou de offerte klaar. Hoor graag van je. 🙂',
  },
  willemsen: {
    naam: 'Familie Willemsen', avatar: 'FW', kanaalIcoon: '📞', kanaal: 'via gemiste oproep',
    berichten: [
      { van: 'systeem', tekst: 'Gemiste oproep van +31 6 24 xx xx xx — Vangst stuurde automatisch een appje.', tijd: 'gisteren 16:20' },
      { van: 'ai', tekst: 'Hallo! U belde net Schildersbedrijf Van Dijk, sorry dat we niet opnamen — we stonden op de steiger. Waarmee kunnen we u helpen?', tijd: 'gisteren 16:20' },
      { van: 'klant', tekst: 'Ha, we willen de woonkamer laten sausen. Wat kost dat ongeveer?', tijd: 'gisteren 16:35' },
      { van: 'ai', tekst: 'Fijn dat u ons belt! Een woonkamer sausen zit meestal tussen de €600 en €900, afhankelijk van de grootte. Zal ik langskomen voor een exacte prijs?', tijd: 'gisteren 16:36' },
    ],
    voorstel: 'Zal ik vrijdagochtend om 09:00 langskomen om het op te nemen? Dan weet u meteen waar u aan toe bent.',
  },
  jansen: {
    naam: 'Anja Jansen', avatar: 'AJ', kanaalIcoon: '🌐', kanaal: 'via websiteformulier',
    berichten: [
      { van: 'klant', tekst: 'Via de website: oud behang verwijderen en slaapkamer opnieuw sausen. Kan dat op korte termijn?', tijd: 'ma 08:15' },
      { van: 'ai', tekst: 'Goedemorgen Anja! Behang eraf en strak opnieuw sausen, dat komt goed. We kunnen deze week al langskomen om het op te nemen.', tijd: 'ma 08:16' },
      { van: 'ai', tekst: 'Woensdag om 10:30 in Gouda schikt bij ons. Komt dat uit?', tijd: 'ma 08:16' },
      { van: 'klant', tekst: 'Woensdag 10:30 is prima!', tijd: 'ma 08:40' },
      { van: 'ai', tekst: 'Top, staat genoteerd! Tot woensdag. 🎨', tijd: 'ma 08:40' },
    ],
    voorstel: 'Fijn! Ik heb woensdag 10:30 voor u in de agenda gezet. Tot dan!',
  },
  vermeer: {
    naam: 'Tim Vermeer', avatar: 'TV', kanaalIcoon: '💬', kanaal: 'via WhatsApp',
    berichten: [
      { van: 'klant', tekst: 'Hoi! De schuur buiten moet in de beits. Kan dat nog dit najaar?', tijd: 'ma 13:05' },
      { van: 'ai', tekst: 'Hoi Tim! Zeker, zolang het weer meezit beitsen we buiten prima door in het najaar. Ik kom even kijken hoeveel werk het is.', tijd: 'ma 13:06' },
      { van: 'klant', tekst: 'Mooi! Wanneer zou je kunnen?', tijd: 'ma 13:20' },
    ],
    voorstel: 'Vrijdag 13 aug om 13:30 ben ik in de buurt, dan loop ik even langs. Schikt dat?',
  },
};

let huidigGesprek = null;
let overnemenActief = false;

function openGesprek(id) {
  const g = gesprekken[id];
  if (!g) return;
  huidigGesprek = id;
  overnemenActief = false;

  document.getElementById('g-naam').textContent = g.naam;
  document.getElementById('g-avatar').textContent = g.avatar;
  document.getElementById('g-via').innerHTML = '<span>' + g.kanaalIcoon + '</span> ' + g.kanaal;

  // Overnemen-knop resetten
  const ovKnop = document.getElementById('overnemen-knop');
  ovKnop.textContent = 'Zelf overnemen';
  ovKnop.classList.remove('actief-modus');
  document.getElementById('voorstel-blok').style.display = 'block';
  document.getElementById('zelf-invoer').classList.remove('actief');

  // Berichten opbouwen
  const bak = document.getElementById('gesprek-berichten');
  bak.innerHTML = '';
  g.berichten.forEach(b => bak.appendChild(maakBubbel(b)));

  // Voorstel invullen
  document.getElementById('voorstel-tekst').textContent = g.voorstel;

  gaNaar('gesprek');
  setTimeout(() => { bak.scrollTop = bak.scrollHeight; }, 30);
}

function maakBubbel(b) {
  // Systeemmelding (bv. gemiste oproep) apart tonen
  if (b.van === 'systeem') {
    const d = document.createElement('div');
    d.className = 'dag-scheiding';
    d.textContent = '📞 ' + b.tekst;
    return d;
  }
  const div = document.createElement('div');
  const vanMij = (b.van === 'ai' || b.van === 'mij');
  div.className = 'bubbel ' + (vanMij ? 'mij' : 'klant');
  let inhoud = '';
  if (b.van === 'ai') inhoud += '<span class="ai-tag">⚡ AI</span>';
  inhoud += b.tekst.replace(/</g, '&lt;');
  inhoud += '<span class="tijd">' + b.tijd + '</span>';
  div.innerHTML = inhoud;
  return div;
}

function wisselOvernemen() {
  overnemenActief = !overnemenActief;
  const ovKnop = document.getElementById('overnemen-knop');
  const voorstel = document.getElementById('voorstel-blok');
  const zelf = document.getElementById('zelf-invoer');

  if (overnemenActief) {
    ovKnop.textContent = '✓ Jij antwoordt';
    ovKnop.classList.add('actief-modus');
    voorstel.style.display = 'none';
    zelf.classList.add('actief');
    toon('Je hebt het gesprek overgenomen');
  } else {
    ovKnop.textContent = 'Zelf overnemen';
    ovKnop.classList.remove('actief-modus');
    voorstel.style.display = 'block';
    zelf.classList.remove('actief');
    toon('Assistent neemt weer over');
  }
}

function verstuurVoorstel() {
  const tekst = document.getElementById('voorstel-tekst').textContent;
  voegBerichtToe({ van: 'ai', tekst: tekst, tijd: 'nu' });
  document.getElementById('voorstel-blok').style.display = 'none';
  toon('Antwoord verstuurd ✓');
}

function verstuurZelf() {
  const veld = document.getElementById('zelf-veld');
  const tekst = veld.value.trim();
  if (!tekst) return;
  voegBerichtToe({ van: 'mij', tekst: tekst, tijd: 'nu' });
  veld.value = '';
  toon('Bericht verstuurd ✓');
}

// Enter = versturen in zelf-typen veld + beginlayout onboarding
document.addEventListener('DOMContentLoaded', () => {
  const veld = document.getElementById('zelf-veld');
  if (veld) veld.addEventListener('keydown', e => { if (e.key === 'Enter') verstuurZelf(); });
  obNaar(1); // normaliseer de layout van stap 1 bij het laden
});

function voegBerichtToe(b) {
  const bak = document.getElementById('gesprek-berichten');
  bak.appendChild(maakBubbel(b));
  bak.scrollTop = bak.scrollHeight;
}

/* ---- Schakelaars (opvolging, kanalen) ---- */
function wisselSchakelaar(el) {
  el.classList.toggle('aan');
  const kaart = el.closest('.opvolg-kaart');
  if (kaart) {
    const uit = !el.classList.contains('aan');
    kaart.classList.toggle('uit', uit);
    const datum = kaart.querySelector('.p-datum');
    if (uit) {
      datum.dataset.vorig = datum.innerHTML;
      datum.textContent = 'Uitgeschakeld';
      toon('Opvolging uitgezet');
    } else if (datum.dataset.vorig) {
      datum.innerHTML = datum.dataset.vorig;
      toon('Opvolging weer aan');
    }
  }
}

/* ---- Toon-keuze in instellingen ---- */
function kiesToon(el) {
  document.querySelectorAll('.toon-optie').forEach(o => o.classList.remove('gekozen'));
  el.classList.add('gekozen');
  toon('Toon aangepast');
}

/* ---- Toast-melding ---- */
let toastTimer = null;
function toon(bericht) {
  const t = document.getElementById('toast');
  t.textContent = bericht;
  t.classList.add('zichtbaar');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('zichtbaar'), 2200);
}
