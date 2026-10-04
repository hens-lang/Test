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

// Vaste trekkingen worden altijd gerespecteerd, de rest blijft eerlijk
const vast = [{ gever: 'Opa', ontvanger: 'Lotte' }, { gever: 'Jeroen', ontvanger: 'Sanne' }];
const lotteKrijgers = new Set();
for (let i = 0; i < 500; i++) {
  const r = L.trek(familie, null, vast);
  const per = Object.fromEntries(r.map(p => [p.gever.naam, p.ontvanger.naam]));
  assert.strictEqual(per.Opa, 'Lotte');
  assert.strictEqual(per.Jeroen, 'Sanne');
  assert.strictEqual(new Set(Object.values(per)).size, familie.length);
  lotteKrijgers.add(per.Sanne);
}
assert.ok(lotteKrijgers.size > 1, 'de rest is nog steeds willekeurig');
assert.throws(() => L.trek(familie, null, [{ gever: 'Opa', ontvanger: 'Opa' }]), /zichzelf/);
assert.throws(() => L.trek(familie, null, [{ gever: 'Opa', ontvanger: 'Lotte' }, { gever: 'Oma', ontvanger: 'Lotte' }]), /twee mensen/);
assert.throws(() => L.trek(familie, null, [{ gever: 'Piet', ontvanger: 'Lotte' }]), /doet niet mee/);

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

assert.strictEqual(L.sleutel(' Zoë  de Vries '), 'zoe-de-vries');
assert.ok(L.controleer([{ naam: 'Zoë' }, { naam: 'Zoe' }, { naam: 'B' }]).length > 0, 'te gelijkende namen');
assert.strictEqual(L.sleutel('!!'), 'naamloos');

// Uitnodiging en wensen-codes (de WhatsApp-route)
const uit = L.maakUitnodiging({ evenement: 'Sint 2026' }, ['Hens (Jr)', 'Zoë']);
assert.deepStrictEqual(L.leesUitnodiging('https://x.nl/#wensen=' + uit), { evenement: 'Sint 2026', namen: ['Hens (Jr)', 'Zoë'] });
assert.strictEqual(L.leesUitnodiging('https://x.nl/#lot=' + code), null);
const chat = '[12:01] Zoë: Mijn wensen!\n' + L.maakWensCode('Zoë', 'Boeken 📚') + '\n[12:05] Mart: hier\n' +
  L.maakWensCode('Mart', 'Oud') + ' en later ' + L.maakWensCode('mart', 'Nieuw: drop');
assert.deepStrictEqual(L.leesWensCodes(chat), [{ naam: 'Zoë', wens: 'Boeken 📚' }, { naam: 'mart', wens: 'Nieuw: drop' }]);
assert.deepStrictEqual(L.leesWensCodes('niks hier SINT-WENS:kapot'), []);

console.log('✔ Alle tests geslaagd');
