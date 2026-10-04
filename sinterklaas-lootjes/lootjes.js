/*
 * Sinterklaas lootjes – kernlogica.
 * Wordt gebruikt door index.html (browser) én door test.js (Node),
 * zodat de trekking en de codes overal precies hetzelfde werken.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.Lootjes = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var VERSIE = 1;
  var SLEUTEL = 'Sinterklaas-Piet-5december';

  function schoon(naam) {
    return String(naam || '').trim().replace(/\s+/g, ' ');
  }
  function sleutelVan(naam) {
    return schoon(naam).toLowerCase();
  }

  /**
   * Controleert de deelnemerslijst en geeft een lijst met foutmeldingen terug.
   * deelnemer = { naam, huishouden?, nietTrekken?: [namen], wens? }
   */
  function controleer(deelnemers) {
    var fouten = [];
    var gezien = {};
    var gezienSleutel = {};
    if (!Array.isArray(deelnemers) || deelnemers.length < 3) {
      fouten.push('Je hebt minimaal 3 deelnemers nodig.');
      return fouten;
    }
    deelnemers.forEach(function (d, i) {
      var k = sleutelVan(d.naam);
      if (!k) fouten.push('Deelnemer ' + (i + 1) + ' heeft geen naam.');
      else if (gezien[k] || gezienSleutel[sleutel(d.naam)]) fouten.push('De naam "' + schoon(d.naam) + '" komt dubbel voor (of lijkt te veel op een andere naam).');
      gezien[k] = true;
      if (k) gezienSleutel[sleutel(d.naam)] = true;
    });
    deelnemers.forEach(function (d) {
      (d.nietTrekken || []).forEach(function (n) {
        if (schoon(n) && !gezien[sleutelVan(n)]) {
          fouten.push(schoon(d.naam) + ' mag "' + schoon(n) + '" niet trekken, maar die naam staat niet in de lijst.');
        }
      });
    });
    return fouten;
  }

  /** Mag `gever` een gedicht maken voor `ontvanger`? */
  function magTrekken(gever, ontvanger) {
    if (sleutelVan(gever.naam) === sleutelVan(ontvanger.naam)) return false;
    var hg = sleutelVan(gever.huishouden), ho = sleutelVan(ontvanger.huishouden);
    if (hg && hg === ho) return false;
    var verboden = (gever.nietTrekken || []).map(sleutelVan);
    return verboden.indexOf(sleutelVan(ontvanger.naam)) === -1;
  }

  function schud(lijst, rnd) {
    var a = lijst.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rnd() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function veiligRandom() {
    var c = (typeof globalThis !== 'undefined' && globalThis.crypto) || null;
    if (c && c.getRandomValues) {
      return function () {
        var buf = new Uint32Array(1);
        c.getRandomValues(buf);
        return buf[0] / 4294967296;
      };
    }
    return Math.random;
  }

  /**
   * Controleert vaste trekkingen: [{ gever, ontvanger }] met namen.
   */
  function controleerVast(deelnemers, vast) {
    var fouten = [];
    var bekend = {};
    deelnemers.forEach(function (d) { bekend[sleutelVan(d.naam)] = true; });
    var gevers = {}, ontvangers = {};
    (vast || []).forEach(function (v) {
      var g = sleutelVan(v.gever), o = sleutelVan(v.ontvanger);
      if (!g || !o) return;
      if (!bekend[g]) fouten.push('Vaste trekking: "' + schoon(v.gever) + '" doet niet mee.');
      else if (!bekend[o]) fouten.push('Vaste trekking: "' + schoon(v.ontvanger) + '" doet niet mee.');
      else if (g === o) fouten.push('Vaste trekking: ' + schoon(v.gever) + ' kan zichzelf niet trekken.');
      else if (gevers[g]) fouten.push('Vaste trekking: ' + schoon(v.gever) + ' staat er twee keer in als trekker.');
      else if (ontvangers[o]) fouten.push('Vaste trekking: ' + schoon(v.ontvanger) + ' wordt door twee mensen getrokken.');
      gevers[g] = true;
      ontvangers[o] = true;
    });
    return fouten;
  }

  /**
   * Trekt de lootjes. Geeft een array terug van { gever, ontvanger } (deelnemer-objecten).
   * `vast` (optioneel) legt trekkingen vast: [{ gever: naam, ontvanger: naam }].
   * Gooit een Error als er geen geldige verdeling mogelijk is.
   */
  function trek(deelnemers, rnd, vast) {
    var fouten = controleer(deelnemers).concat(controleerVast(deelnemers, vast));
    if (fouten.length) throw new Error(fouten.join('\n'));
    rnd = rnd || veiligRandom();

    var vastVoor = {};
    (vast || []).forEach(function (v) {
      if (schoon(v.gever) && schoon(v.ontvanger)) vastVoor[sleutelVan(v.gever)] = sleutelVan(v.ontvanger);
    });

    var n = deelnemers.length;
    // Moeilijkste gevers (minste opties) eerst: sneller en altijd een oplossing als die bestaat.
    var opties = deelnemers.map(function (g) {
      var doel = vastVoor[sleutelVan(g.naam)];
      if (doel) return deelnemers.filter(function (o) { return sleutelVan(o.naam) === doel; });
      return deelnemers.filter(function (o) { return magTrekken(g, o); });
    });
    var volgorde = schud(deelnemers.map(function (_, i) { return i; }), rnd)
      .sort(function (a, b) { return opties[a].length - opties[b].length; });

    var bezet = {};
    var resultaat = new Array(n);
    var stappen = 0;

    function zoek(pos) {
      if (pos === n) return true;
      if (++stappen > 200000) return false;
      var gi = volgorde[pos];
      var kandidaten = schud(opties[gi], rnd);
      for (var k = 0; k < kandidaten.length; k++) {
        var key = sleutelVan(kandidaten[k].naam);
        if (bezet[key]) continue;
        bezet[key] = true;
        resultaat[gi] = kandidaten[k];
        if (zoek(pos + 1)) return true;
        bezet[key] = false;
      }
      return false;
    }

    if (!zoek(0)) {
      throw new Error('Met deze regels (huishoudens / "niet trekken") is geen eerlijke verdeling mogelijk. Haal een paar beperkingen weg.');
    }
    return deelnemers.map(function (g, i) { return { gever: g, ontvanger: resultaat[i] }; });
  }

  // ---------- Codes: per deelnemer een geheime code / link ----------

  function naarBytes(str) {
    return typeof TextEncoder !== 'undefined'
      ? new TextEncoder().encode(str)
      : Uint8Array.from(Buffer.from(str, 'utf8'));
  }
  function vanBytes(bytes) {
    return typeof TextDecoder !== 'undefined'
      ? new TextDecoder().decode(bytes)
      : Buffer.from(bytes).toString('utf8');
  }
  function b64url(bytes) {
    var bin = '';
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    var b64 = typeof btoa !== 'undefined' ? btoa(bin) : Buffer.from(bin, 'binary').toString('base64');
    return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function vanB64url(s) {
    s = s.replace(/-/g, '+').replace(/_/g, '/');
    while (s.length % 4) s += '=';
    var bin = typeof atob !== 'undefined' ? atob(s) : Buffer.from(s, 'base64').toString('binary');
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  function husselBytes(bytes) {
    // Simpele versluiering zodat niemand per ongeluk een naam in de link leest.
    var sleutel = naarBytes(SLEUTEL);
    var out = new Uint8Array(bytes.length);
    for (var i = 0; i < bytes.length; i++) out[i] = bytes[i] ^ sleutel[i % sleutel.length] ^ (i * 31 & 255);
    return out;
  }

  /** Maakt de geheime code voor één trekking. `info` = { evenement, datum, budget, deadline } */
  function maakCode(paar, info) {
    info = info || {};
    var data = {
      v: VERSIE,
      g: schoon(paar.gever.naam),
      o: schoon(paar.ontvanger.naam),
      w: schoon(paar.ontvanger.wens),
      e: schoon(info.evenement),
      d: schoon(info.datum),
      b: schoon(info.budget),
      l: schoon(info.deadline)
    };
    return b64url(husselBytes(naarBytes(JSON.stringify(data))));
  }

  /** Leest een code (of een volledige link met #code) terug. Geeft null bij een ongeldige code. */
  function leesCode(codeOfLink) {
    try {
      var s = String(codeOfLink || '').trim();
      var hekje = s.indexOf('#');
      if (hekje !== -1) s = s.slice(hekje + 1);
      s = s.replace(/^lot=/, '');
      var data = JSON.parse(vanBytes(husselBytes(vanB64url(s))));
      if (!data || data.v !== VERSIE || !data.g || !data.o) return null;
      return {
        gever: data.g, ontvanger: data.o, wens: data.w || '',
        evenement: data.e || '', datum: data.d || '', budget: data.b || '', deadline: data.l || ''
      };
    } catch (e) {
      return null;
    }
  }

  /** Veilige, vaste sleutel voor een naam (bruikbaar als document-id). "Zoë de Vries" -> "zoe-de-vries" */
  function sleutel(naam) {
    var k = sleutelVan(naam);
    if (k.normalize) k = k.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return k.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'naamloos';
  }

  /** Zet tekst "Anna, Piet; Klaas" om naar ['Anna','Piet','Klaas']. */
  function splitsNamen(tekst) {
    return String(tekst || '').split(/[,;\n]/).map(schoon).filter(Boolean);
  }

  return {
    controleer: controleer,
    controleerVast: controleerVast,
    magTrekken: magTrekken,
    trek: trek,
    maakCode: maakCode,
    leesCode: leesCode,
    splitsNamen: splitsNamen,
    sleutel: sleutel
  };
});
