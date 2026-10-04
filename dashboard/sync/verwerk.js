// Verwerkt rapportages en het KPI-bord-bronbestand buiten het dashboard om (voor de geplande Claude-taak).
// Gebruikt dezelfde functies als het dashboard: ze worden uit dashboard/index.html geladen, zodat de rekenregels
// nooit uit elkaar lopen.
//
// node verwerk.js <dbmap> <rapmap> <uitmap>
//   dbmap : ArtifactData-export (list met out_dir) met projecten/, resultaten/, klanten/, rapportages/, sync/
//   rapmap: per nieuwe rapportage <fileId>.json = {id, title, modifiedTime, viewUrl, text}
//   uitmap: writes.json (ArtifactData batch-entries, zonder if_version) + docs/*.json + bron.json (als het bord
//           een nieuw bronbestand nodig heeft) + samenvatting.txt
const fs = require('fs'), path = require('path');
if (process.argv[2] === '--bekend') {
  // lijst van al verwerkte rapportages (id, modified, versie) om te vergelijken met de Drive-zoekresultaten
  const dir = require('path').join(process.argv[3], 'rapportages');
  const html0 = require('fs').readFileSync(require('path').join(__dirname, '..', 'index.html'), 'utf8');
  const v = Number((/versie: (\d+) \}/.exec(html0) || [])[1] || 1);
  console.log('parserversie ' + v);
  if (require('fs').existsSync(dir)) require('fs').readdirSync(dir).forEach(f => { const d = JSON.parse(require('fs').readFileSync(require('path').join(dir, f), 'utf8')); console.log(f.slice(0, -5), d.modified, 'versie ' + (d.versie || 1)); });
  process.exit(0);
}
const [dbmap, rapmap, uitmap] = process.argv.slice(2);
if (!dbmap || !rapmap || !uitmap) { console.error('gebruik: node verwerk.js <dbmap> <rapmap> <uitmap>'); process.exit(1); }

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
function grab(naam) {
  const i = html.search(new RegExp('\\n(function ' + naam + '\\(|const ' + naam + ' = )'));
  if (i < 0) throw new Error('niet gevonden in index.html: ' + naam);
  const start = i + 1;
  if (html.startsWith('const', start)) return html.slice(start, html.indexOf(';\n', start) + 1);
  let d = 0;
  for (let k = html.indexOf('{', start); k < html.length; k++) {
    if (html[k] === '{') d++; else if (html[k] === '}' && !--d) return html.slice(start, k + 1);
  }
}

const S = {};
['klanten', 'projecten', 'resultaten', 'rapportages', 'sync'].forEach(c => {
  S[c] = {};
  const dir = path.join(dbmap, c);
  if (fs.existsSync(dir)) fs.readdirSync(dir).filter(f => f.endsWith('.json')).forEach(f => {
    const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    S[c][f.slice(0, -5)] = d && d.data && d.id ? d.data : d;
  });
});
const klant = id => S.klanten[id];
const project = id => S.projecten[id];
// eslint-disable-next-line no-eval
eval(['iso', 'addDays', 'parseISO', 'mondayOf', 'isoWeek', 'weekMonday', 'num', 'sortBy', 'list', 'telt', 'wkStr',
  'BORD_ID', 'bordId', 'kpibordBron', 'hashStr', 'rapNorm', 'rapProject', 'rapUitkomst', 'rapParse'].map(grab).join('\n'));
const RAP_VERSIE = Number((/versie: (\d+) \}/.exec(html) || [])[1] || 1);

const writes = [], log = [];
fs.mkdirSync(path.join(uitmap, 'docs'), { recursive: true });
function zet(collection, doc_id, data) {
  // staat het document al in de wachtrij (bijv. projecten), dan overschrijven
  S[collection][doc_id] = data;
  const file = path.join(uitmap, 'docs', collection + '__' + doc_id + '.json');
  fs.writeFileSync(file, JSON.stringify(data));
  const i = writes.findIndex(w => w.collection === collection && w.doc_id === doc_id);
  const w = { op: 'set', collection, doc_id, file_path: path.resolve(file), bestaat: !!S._bestond[collection + '/' + doc_id] };
  if (i >= 0) writes[i] = w; else writes.push(w);
}
S._bestond = {};
['klanten', 'projecten', 'resultaten', 'rapportages', 'sync'].forEach(c => Object.keys(S[c]).forEach(id => { S._bestond[c + '/' + id] = true; }));

const nu = new Date().toISOString();
const raps = fs.existsSync(rapmap) ? fs.readdirSync(rapmap).filter(f => f.endsWith('.json')).map(f => JSON.parse(fs.readFileSync(path.join(rapmap, f), 'utf8'))) : [];
raps.forEach(f => {
  const d = rapParse(f.text || '', f.title);
  const p = d.week ? rapProject(d.klantNaam, d.jaar, d.week) : null;
  const leesbaar = d.cijfers.pogingen != null;
  const rec = { titel: f.title, link: f.viewUrl || '', modified: f.modifiedTime, versie: RAP_VERSIE, gelezen: nu, projectId: p ? p.id : null, ...(leesbaar ? {} : { onleesbaar: true }), ...d };
  if (p && leesbaar) {
    const rid = p.id + '_' + wkStr(d.jaar, d.week), r = S.resultaten[rid];
    const telR = telt(p.id, d.cijfers);
    const rap = { bestand: f.title.replace(/\.pdf$/i, ''), link: rec.link, gecontroleerd: true, cijfers: d.cijfers,
      tekst: [d.cijfers.afspraak ? d.cijfers.afspraak + ' afspra' + (d.cijfers.afspraak === 1 ? 'ak' : 'ken') : '', d.cijfers.overdracht ? d.cijfers.overdracht + ' overdr.' : ''].filter(Boolean).join(', ') || '0',
      ...(d.afspraken.length ? { afspraken: d.afspraken } : {}) };
    if (r && r.bron === 'rapportage') zet('resultaten', rid, { ...r, afspraak: d.cijfers.afspraak, overdracht: d.cijfers.overdracht, pogingen: d.cijfers.pogingen || 0, gesproken: d.cijfers.gesproken || 0, rapportage: rap });
    else if (r) {
      const telE = telt(p.id, r);
      if (telE !== telR) { rap.gecontroleerd = false; rap.verschil = 'rapportage ' + telR + ', export ' + telE; }
      zet('resultaten', rid, { ...r, rapportage: rap });
    } else zet('resultaten', rid, { projectId: p.id, jaar: d.jaar, week: d.week, bron: 'rapportage', ingelezen: nu,
      afspraak: d.cijfers.afspraak, overdracht: d.cijfers.overdracht, pogingen: d.cijfers.pogingen || 0, gesproken: d.cijfers.gesproken || 0,
      warm: d.cijfers.warm || 0, terugbel: d.cijfers.terugbel || 0, geenInteresse: d.cijfers.geenInteresse || 0, infomail: d.cijfers.infomail || 0, rapportage: rap });
    const ins = S.projecten[p.id].inzicht || {};
    const insK = ins.week ? num(ins.jaar || d.jaar) * 100 + num(ins.week) : 0;
    if (insK <= d.jaar * 100 + d.week && (d.focus.length || d.hoorden.length))
      zet('projecten', p.id, { ...S.projecten[p.id], inzicht: { bron: 'Rapportage wk ' + d.week, week: d.week, jaar: d.jaar, link: rec.link,
        focus: d.focus, hoorden: d.hoorden, terugbelOpen: d.cijfers.terugbel, infomails: d.cijfers.infomail, kort: d.kort } });
    log.push(f.title + ' -> ' + p.naam + ' (' + telR + (rap.verschil ? ', ' + rap.verschil : '') + ')');
  } else log.push(f.title + ' -> ' + (p ? 'niet leesbaar' : 'NIET GEKOPPELD'));
  zet('rapportages', f.id, rec);
});

// KPI-bord: nieuw bronbestand nodig?
const b = kpibordBron(), h = hashStr(JSON.stringify(b));
if (b.klanten.length && (S.sync.kpibord || {}).hash !== h) {
  fs.writeFileSync(path.join(uitmap, 'bron.json'), JSON.stringify({ ...b, gemaakt: nu.slice(0, 19) + 'Z' }));
  zet('sync', 'kpibord', { ...(S.sync.kpibord || {}), hash: h, bronGeschreven: nu });
  log.push('KPI-bord: nieuw bronbestand (bron.json) uploaden');
} else log.push('KPI-bord: bron is actueel');

fs.writeFileSync(path.join(uitmap, 'writes.json'), JSON.stringify(writes, null, 1));
fs.writeFileSync(path.join(uitmap, 'samenvatting.txt'), log.join('\n') + '\n');
console.log(log.join('\n'));
console.log(writes.length + ' writes (' + writes.filter(w => w.bestaat).length + ' op bestaande documenten, if_version nodig)');
