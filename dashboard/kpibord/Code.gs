// LINK. KPI-bord — server (Google Apps Script)
// Handmatige tellingen (+/−) staan in Script Properties; tellen gaat atomair met een lock.
// Realtime koppeling met het management dashboard, via de Drive-map "LINK. KPI-bord bron":
// - het dashboard schrijft bij elke wijziging (targets, werkperiodes, nieuwe belexport) een nieuw
//   kpibord-bron.json; het bord leest altijd het nieuwste (hooguit 1 minuut oud)
// - elke +/− schrijft het bord meteen in het Google Doc "KPI-bord stand"; het dashboard leest dat elke minuut

const BRON_MAP = "LINK. KPI-bord bron";
const STAND_DOC = "KPI-bord stand";

function doGet(e) {
  if (e && e.parameter && e.parameter.get === "state") {
    return ContentService.createTextOutput(JSON.stringify(getState()))
      .setMimeType(ContentService.MimeType.JSON);
  }
  return HtmlService.createHtmlOutputFromFile("Index")
    .setTitle("LINK. KPI-bord")
    .addMetaTag("viewport", "width=device-width, initial-scale=1")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function handmatig() {
  const raw = PropertiesService.getScriptProperties().getProperty("state");
  return raw ? JSON.parse(raw) : { weeks: {} };
}

// Nieuwste kpibord-bron.json uit de bronmap; 1 minuut gecachet. Oudere versies gaan naar de prullenbak
// (de laatste 3 blijven staan). Lukt het lezen niet, dan draait het bord door op de ingebouwde lijst.
function bron() {
  const cache = CacheService.getScriptCache();
  const hit = cache.get("bron");
  if (hit) return JSON.parse(hit);
  let data = null;
  try {
    const mappen = DriveApp.getFoldersByName(BRON_MAP);
    if (mappen.hasNext()) {
      const files = [];
      const it = mappen.next().getFilesByName("kpibord-bron.json");
      while (it.hasNext()) files.push(it.next());
      files.sort(function (a, b) { return b.getDateCreated() - a.getDateCreated(); });
      if (files.length) data = JSON.parse(files[0].getBlob().getDataAsString());
      files.slice(3).forEach(function (f) { try { f.setTrashed(true); } catch (err) {} });
    }
  } catch (err) {
    data = null;
  }
  if (data) cache.put("bron", JSON.stringify(data), 60);
  return data;
}

function getState() {
  const s = handmatig();
  s.bron = bron();
  return s;
}

// delta = +1 of -1 voor klant `id` in week `weekKey` (bijv. "2026-W36")
function bump(weekKey, id, delta) {
  const lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    const props = PropertiesService.getScriptProperties();
    const state = JSON.parse(props.getProperty("state") || '{"weeks":{}}');
    if (!state.weeks[weekKey]) state.weeks[weekKey] = {};
    const cur = state.weeks[weekKey][id] || 0;
    state.weeks[weekKey][id] = Math.max(0, cur + delta);
    props.setProperty("state", JSON.stringify(state));
    schrijfStand(state);
  } finally {
    lock.releaseLock();
  }
  return getState();
}

// Stand van de laatste 8 weken in het Google Doc "KPI-bord stand" (één regel JSON tussen KPIBORD en EINDE).
// Mislukt dit, dan telt het bord gewoon door; de volgende tik probeert het opnieuw.
function schrijfStand(state) {
  try {
    const props = PropertiesService.getScriptProperties();
    let id = props.getProperty("standDoc");
    if (!id) {
      const mappen = DriveApp.getFoldersByName(BRON_MAP);
      if (!mappen.hasNext()) return;
      const it = mappen.next().getFilesByName(STAND_DOC);
      if (!it.hasNext()) return;
      id = it.next().getId();
      props.setProperty("standDoc", id);
    }
    const weeks = {};
    Object.keys(state.weeks).sort().slice(-8).forEach(function (k) { weeks[k] = state.weeks[k]; });
    DocumentApp.openById(id).getBody().setText("KPIBORD " + JSON.stringify({ bijgewerkt: new Date().toISOString(), weeks: weeks }) + " EINDE");
  } catch (err) {
    PropertiesService.getScriptProperties().deleteProperty("standDoc");
  }
}

// Eenmalig uitvoeren vanuit de editor om Drive-toegang te geven en de bron te testen.
function testBron() {
  CacheService.getScriptCache().remove("bron");
  const b = bron();
  Logger.log(b ? "Bron gevonden: " + b.klanten.length + " opdrachtgevers, gemaakt " + b.gemaakt : "Geen bron gevonden in map " + BRON_MAP);
  schrijfStand(handmatig());
  Logger.log(PropertiesService.getScriptProperties().getProperty("standDoc") ? "Stand geschreven naar " + STAND_DOC : "Doc " + STAND_DOC + " niet gevonden");
}
