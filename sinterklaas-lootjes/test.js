// Draai met: node test.js
const assert = require('assert');
const L = require('./lootjes');

const familie = [
  { naam: 'Oma', huishouden: 'opa-oma' },
  { naam: 'Opa', huishouden: 'opa-oma' },
  { naam: 'Sanne', huishouden: 'sanne' },
  { naam: 'Mark', huishouden: 'sanne' },
  { naam: 'Lotte', nietTrekken: ['Mark'] },
  { naam: 'Jeroen', wens: 'Houdt van voetbal en drop' }
];

for (let i = 0; i < 2000; i++) {
  const r = L.trek(familie);
  const ontvangers = new Set(r.map(p => p.ontvanger.naam));
  assert.strictEqual(ontvangers.size, familie.length, 'iedereen krijgt precies één gedicht');
  r.forEach(p => assert.ok(L.magTrekken(p.gever, p.ontvanger), `${p.gever.naam} -> ${p.ontvanger.naam} mag niet`));
}

// Code heen en terug, inclusief bijzondere tekens
const paar = { gever: { naam: 'Zoë' }, ontvanger: { naam: 'Sinterklaas', wens: 'Pepernoten & 🎁' } };
const code = L.maakCode(paar, { evenement: 'Pakjesavond', budget: '€ 15', datum: '5 december' });
const terug = L.leesCode('https://voorbeeld.nl/index.html#lot=' + code);
assert.strictEqual(terug.gever, 'Zoë');
assert.strictEqual(terug.ontvanger, 'Sinterklaas');
assert.strictEqual(terug.wens, 'Pepernoten & 🎁');
assert.strictEqual(terug.budget, '€ 15');
assert.ok(!code.includes('Sinterklaas'), 'naam is niet leesbaar in de code');
assert.strictEqual(L.leesCode('onzin'), null);

// Fouten
assert.ok(L.controleer([{ naam: 'A' }, { naam: 'B' }]).length > 0, 'minimaal 3');
assert.ok(L.controleer([{ naam: 'A' }, { naam: 'a' }, { naam: 'B' }]).length > 0, 'dubbele naam');
assert.throws(() => L.trek([
  { naam: 'A', huishouden: 'x' }, { naam: 'B', huishouden: 'x' }, { naam: 'C', huishouden: 'x' }
]), /geen eerlijke verdeling/);

assert.deepStrictEqual(L.splitsNamen(' Anna, Piet ;Klaas\n'), ['Anna', 'Piet', 'Klaas']);

console.log('✔ Alle tests geslaagd');
