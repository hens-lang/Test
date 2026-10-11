#!/usr/bin/env node
// Trekt de lootjes en maakt één link voor de hele familie-app.
// Gebruik: node maak-groepslink.js instellingen.json
//
// instellingen.json (houd dit bestand privé, zet het niet in de repository):
// {
//   "url": "https://hens-lang.github.io/Test/sinterklaas-lootjes/",
//   "info": { "evenement": "...", "datum": "...", "budget": "...", "deadline": "..." },
//   "personen": [ { "naam": "...", "huishouden": "...", "nietTrekken": [] } ],
//   "vast": [ { "gever": "...", "ontvanger": "..." } ]
// }
const fs = require('fs');
const L = require('./lootjes');

const pad = process.argv[2];
if (!pad) {
  console.error('Gebruik: node maak-groepslink.js instellingen.json');
  process.exit(1);
}
const cfg = JSON.parse(fs.readFileSync(pad, 'utf8'));
const paren = L.trek(cfg.personen, null, cfg.vast || []);
const link = (cfg.url || 'https://hens-lang.github.io/Test/sinterklaas-lootjes/') + '#groep=' + L.maakGroepsCode(paren, cfg.info);

// Controle: elke naam in de link geeft het juiste lootje terug.
const terug = L.leesGroepsCode(link);
paren.forEach(p => {
  if (terug.lootje(p.gever.naam).ontvanger !== p.ontvanger.naam) throw new Error('Controle mislukt voor ' + p.gever.naam);
});
(cfg.vast || []).forEach(v => {
  if (terug.lootje(v.gever).ontvanger !== v.ontvanger) throw new Error('Vaste trekking niet toegepast: ' + v.gever);
});
console.log(link);
