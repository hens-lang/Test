#!/usr/bin/env node
// Trekt de lootjes en maakt voor iedereen een eigen, geheime link.
// In elke link staat alléén het lootje van die persoon.
// Gebruik: node maak-links.js instellingen.json [verstuurpagina.html]
//
// instellingen.json heeft dezelfde opbouw als bij maak-groepslink.js (houd het privé).
// Met een tweede argument wordt ook een verstuurpagina gemaakt: per naam een WhatsApp-knop.
const fs = require('fs');
const L = require('./lootjes');

const [pad, htmlPad] = process.argv.slice(2);
if (!pad) {
  console.error('Gebruik: node maak-links.js instellingen.json [verstuurpagina.html]');
  process.exit(1);
}
const cfg = JSON.parse(fs.readFileSync(pad, 'utf8'));
const basis = cfg.url || 'https://hens-lang.github.io/Test/sinterklaas-lootjes/';
const paren = L.trek(cfg.personen, null, cfg.vast || []);

const links = paren.map(p => {
  const link = basis + '#lot=' + L.maakCode(p, cfg.info);
  // Controle: de link geeft precies dit lootje terug en bevat geen leesbare namen.
  const terug = L.leesCode(link);
  if (terug.gever !== p.gever.naam || terug.ontvanger !== p.ontvanger.naam) throw new Error('Controle mislukt: ' + p.gever.naam);
  return {
    naam: p.gever.naam,
    link,
    bericht: 'Hoi ' + p.gever.naam + '! 🎅 Hier is jouw geheime Sinterklaas-lootje' +
      (cfg.info.evenement ? ' voor de ' + cfg.info.evenement : '') +
      '. Open hem als niemand meekijkt, en stuur hem niet door:\n' + link
  };
});
(cfg.vast || []).forEach(v => {
  const l = links.find(x => x.naam === v.gever);
  if (L.leesCode(l.link).ontvanger !== v.ontvanger) throw new Error('Vaste trekking niet toegepast: ' + v.gever);
});

if (htmlPad) {
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  const rijen = links.map((l, i) => `
      <li class="rij" id="rij${i}">
        <span class="naam">${esc(l.naam)}</span>
        <span class="knoppen">
          <a class="knop wa" href="https://wa.me/?text=${encodeURIComponent(l.bericht)}" target="_blank" rel="noopener" data-rij="rij${i}">WhatsApp</a>
          <button class="knop" data-kopie="${esc(l.bericht)}" data-rij="rij${i}">Kopieer</button>
        </span>
      </li>`).join('');
  fs.writeFileSync(htmlPad, `<title>Lootjes Versturen</title>
<link href="https://fonts.googleapis.com/css2?family=Gloock&family=Instrument+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root { color-scheme: dark; --nacht:#12090f; --fluweel:#24101a; --rand:rgba(217,180,90,.22); --zacht:rgba(246,239,226,.08);
    --ivoor:#f6efe2; --mist:#bfaeb0; --rood:#b3172e; --goud:#d9b45a; --groen:#7fd1a0; }
  body { margin:0; background:radial-gradient(ellipse 70% 40% at 50% -10%, rgba(214,58,79,.25), transparent 70%), var(--nacht);
    color:var(--ivoor); font:16px/1.55 "Instrument Sans", system-ui, sans-serif; }
  main { max-width:640px; margin:0 auto; padding:0 16px; padding-block:40px 64px; }
  .oog { font-size:12px; font-weight:600; letter-spacing:.22em; text-transform:uppercase; color:var(--goud); }
  h1 { font:400 clamp(34px,8vw,52px)/1.1 Gloock, Georgia, serif; margin:8px 0 10px; color:var(--goud); }
  p { color:var(--mist); margin:0 0 8px; }
  .voortgang { margin:22px 0 10px; font-weight:600; color:var(--ivoor); font-variant-numeric:tabular-nums; }
  ol { list-style:none; padding:0; margin:0; border:1px solid var(--zacht); border-radius:18px; background:var(--fluweel); }
  .rij { display:flex; flex-wrap:wrap; gap:8px 12px; align-items:center; justify-content:space-between; padding:14px 18px; border-top:1px solid var(--zacht); }
  .rij:first-child { border-top:none; }
  .naam { font:400 21px/1.2 Gloock, Georgia, serif; }
  .rij.klaar .naam { color:var(--groen); }
  .rij.klaar .naam::after { content:" ✓"; font:600 15px "Instrument Sans", sans-serif; }
  .knoppen { display:flex; gap:6px; }
  .knop { font:600 14px "Instrument Sans", sans-serif; color:var(--ivoor); background:rgba(246,239,226,.06); border:1px solid var(--rand);
    border-radius:999px; padding:8px 15px; text-decoration:none; cursor:pointer; }
  .knop.wa { background:linear-gradient(180deg,#d63a4f,var(--rood)); border-color:transparent; color:#fff; }
  .knop:focus-visible { outline:2px solid var(--goud); outline-offset:2px; }
  textarea { width:100%; margin-top:8px; font:13px/1.4 monospace; background:rgba(0,0,0,.3); color:var(--ivoor); border:1px solid var(--rand); border-radius:10px; padding:8px; }
  .let { margin-top:22px; font-size:14px; border:1px solid var(--rand); border-radius:14px; padding:12px 14px; background:rgba(217,180,90,.07); color:var(--ivoor); }
</style>
<main>
  <p class="oog">${esc(cfg.info.evenement || 'Sinterklaas')}</p>
  <h1>Lootjes versturen</h1>
  <p>Tik bij elke naam op <b>WhatsApp</b>, kies die persoon als contact en druk op verzenden. Elke link bevat alleen het lootje van die ene persoon.</p>
  <p class="voortgang" id="voortgang">0 van ${links.length} verstuurd</p>
  <ol>${rijen}
  </ol>
  <p class="let">Klik zelf niet op de links in de berichten, dan blijft het ook voor jou een verrassing. Deze pagina is alleen voor jou: deel hem niet.</p>
</main>
<script>
  var KLAAR = 'lootjes-verstuurd';
  var klaar = {};
  try { klaar = JSON.parse(localStorage.getItem(KLAAR)) || {}; } catch (e) { klaar = {}; }
  function markeer(id) {
    klaar[id] = true;
    try { localStorage.setItem(KLAAR, JSON.stringify(klaar)); } catch (e) {}
    toon();
  }
  function toon() {
    var n = 0;
    document.querySelectorAll('.rij').forEach(function (r) { var k = !!klaar[r.id]; r.classList.toggle('klaar', k); if (k) n++; });
    document.getElementById('voortgang').textContent = n + ' van ${links.length} verstuurd';
  }
  document.querySelectorAll('a.wa').forEach(function (a) { a.addEventListener('click', function () { markeer(a.dataset.rij); }); });
  document.querySelectorAll('button[data-kopie]').forEach(function (b) {
    b.addEventListener('click', function () {
      var tekst = b.dataset.kopie;
      var klaarMet = function () { b.textContent = 'Gekopieerd ✓'; setTimeout(function () { b.textContent = 'Kopieer'; }, 1500); markeer(b.dataset.rij); };
      var handmatig = function () {
        var rij = document.getElementById(b.dataset.rij);
        var vak = rij.querySelector('textarea') || rij.appendChild(document.createElement('textarea'));
        vak.value = tekst; vak.readOnly = true; vak.focus(); vak.select(); markeer(b.dataset.rij);
      };
      try { navigator.clipboard.writeText(tekst).then(klaarMet, handmatig); } catch (e) { handmatig(); }
    });
  });
  toon();
</script>
`);
}
console.log(JSON.stringify(links.map(l => ({ naam: l.naam, link: l.link })), null, 2));
