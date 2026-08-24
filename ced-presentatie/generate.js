// Genereert: CED-directiepresentatie-voorbeeld.pptx
// Voorbeeld-kwartaalpresentatie voor de directie van CED (alle cijfers fictief).
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const {
  FiTruck, FiHome, FiHeart, FiZap, FiClock, FiSmile, FiTrendingUp,
  FiTrendingDown, FiAlertTriangle, FiUsers, FiDatabase, FiCloudRain,
  FiCheckCircle, FiTarget, FiCalendar, FiCpu, FiMessageCircle, FiShield,
  FiFileText, FiLayers, FiMonitor,
} = require("react-icons/fi");

// ---------- palet ----------
const NAVY = "1E2A52";      // dominant
const NAVY_DEEP = "131C3A"; // donkere achtergronden
const ICE = "CADCFC";       // licht blauw
const CARD = "EEF3FB";      // kaart-tint
const ACCENT = "F2A900";    // amber accent
const GREEN = "2E9E6B";
const RED = "C4453B";
const GREY = "5B6472";
const WHITE = "FFFFFF";

const HEAD = "Cambria";
const BODY = "Calibri";

// ---------- iconen ----------
async function iconData(Icon, color) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Icon, { color: "#" + color, size: 256, strokeWidth: 2 })
  );
  const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const icons = {};
  const wanted = {
    truck: [FiTruck, WHITE], home: [FiHome, WHITE], heart: [FiHeart, WHITE],
    zap: [FiZap, WHITE], zapNavy: [FiZap, NAVY], clock: [FiClock, WHITE],
    smile: [FiSmile, WHITE], up: [FiTrendingUp, WHITE], down: [FiTrendingDown, WHITE],
    alert: [FiAlertTriangle, WHITE], users: [FiUsers, WHITE], db: [FiDatabase, WHITE],
    rain: [FiCloudRain, WHITE], check: [FiCheckCircle, WHITE], target: [FiTarget, WHITE],
    cal: [FiCalendar, WHITE], cpu: [FiCpu, WHITE], msg: [FiMessageCircle, WHITE],
    shield: [FiShield, WHITE], file: [FiFileText, WHITE], layers: [FiLayers, WHITE],
    monitor: [FiMonitor, WHITE], upGreen: [FiTrendingUp, GREEN],
  };
  for (const [k, [I, c]] of Object.entries(wanted)) icons[k] = await iconData(I, c);

  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
  pres.author = "CED";
  pres.title = "CED Directie-update Q2 2026 (voorbeeld)";

  const W = 13.33;

  // herbruikbare bouwstenen -------------------------------------------------
  function slideTitle(slide, kicker, title) {
    slide.addText(kicker.toUpperCase(), {
      x: 0.6, y: 0.38, w: 9.5, h: 0.3, margin: 0,
      fontFace: BODY, fontSize: 11, bold: true, color: ACCENT, charSpacing: 3,
    });
    slide.addText(title, {
      x: 0.6, y: 0.62, w: 11.0, h: 0.75, margin: 0,
      fontFace: HEAD, fontSize: 30, bold: true, color: NAVY,
    });
    slide.addText("CED  ·  Directie-update Q2 2026  ·  voorbeeldcijfers, illustratief", {
      x: 0.6, y: 7.08, w: 8.0, h: 0.28, margin: 0,
      fontFace: BODY, fontSize: 9, color: GREY,
    });
    // woordmerk rechtsboven (vervang t.z.t. door officieel logobestand)
    slide.addText("CED", {
      x: 11.53, y: 0.4, w: 1.2, h: 0.45, margin: 0, align: "right",
      fontFace: HEAD, fontSize: 20, bold: true, color: NAVY,
    });
  }

  function iconCircle(slide, key, x, y, d, fill) {
    slide.addShape("ellipse", { x, y, w: d, h: d, fill: { color: fill } });
    const pad = d * 0.26;
    slide.addImage({ data: icons[key], x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
  }

  // ---------- 1 · titel ----------
  {
    const s = pres.addSlide();
    s.background = { color: NAVY_DEEP };
    // rustige decoratie: grote translucente cirkels rechts
    s.addShape("ellipse", { x: 9.4, y: -2.1, w: 6.4, h: 6.4, fill: { color: NAVY, transparency: 35 } });
    s.addShape("ellipse", { x: 11.1, y: 3.9, w: 4.6, h: 4.6, fill: { color: "24356B", transparency: 45 } });
    s.addShape("ellipse", { x: 9.3, y: 5.9, w: 1.15, h: 1.15, fill: { color: ACCENT } });

    s.addText("CED", {
      x: 0.85, y: 0.75, w: 3.0, h: 0.9, margin: 0,
      fontFace: HEAD, fontSize: 40, bold: true, color: WHITE,
    });
    s.addText("Schade-expertise & Claims Management", {
      x: 0.85, y: 1.55, w: 6.5, h: 0.35, margin: 0,
      fontFace: BODY, fontSize: 13, color: ICE,
    });

    s.addText("Directie-update\nQ2 2026", {
      x: 0.85, y: 2.85, w: 9.5, h: 2.0, margin: 0,
      fontFace: HEAD, fontSize: 54, bold: true, color: WHITE, lineSpacing: 60,
    });
    s.addText("Resultaten, digitalisering en beslispunten voor het tweede halfjaar", {
      x: 0.85, y: 4.95, w: 7.6, h: 0.5, margin: 0,
      fontFace: BODY, fontSize: 16, italic: true, color: ICE,
    });

    s.addText("[Naam presentator]  ·  [Functie]      |      24 augustus 2026      |      Vertrouwelijk — alleen voor intern gebruik", {
      x: 0.85, y: 6.55, w: 10.5, h: 0.35, margin: 0,
      fontFace: BODY, fontSize: 11, color: "8FA3C8",
    });
    s.addNotes(
      "Welkom. Doel van vandaag: de directie in 20 minuten meenemen in de Q2-resultaten, " +
      "de voortgang van de digitalisering (Instant Expertise) en drie concrete beslispunten. " +
      "Alle cijfers in dit voorbeeld zijn fictief — vervang ze door de werkelijke kwartaalcijfers."
    );
  }

  // ---------- 2 · managementsamenvatting ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    slideTitle(s, "Managementsamenvatting", "Q2 in één oogopslag: groei én snellere afhandeling");

    s.addText([
      { text: "Kernboodschap\n", options: { fontSize: 15, bold: true, color: NAVY, paraSpaceAfter: 8 } },
      { text: "Het dossiervolume groeide in alle drie de domeinen, terwijl de gemiddelde doorlooptijd juist daalde. De uitrol van Instant Expertise® is daarvan de belangrijkste motor: bijna twee derde van de geschikte dossiers loopt inmiddels digitaal.\n", options: { fontSize: 13.5, color: "333B49", paraSpaceAfter: 10 } },
      { text: "Voor H2 vragen wij de directie om drie besluiten: de investering in AI-triage, capaciteitsuitbreiding bij Vitality en de go/no-go voor het nieuwe klantportaal.", options: { fontSize: 13.5, color: "333B49" } },
    ], { x: 0.6, y: 1.75, w: 5.4, h: 4.6, margin: 0, fontFace: BODY, valign: "top" });

    const stats = [
      { n: "128.400", l: "afgehandelde dossiers", d: "+6% t.o.v. Q2 2025", dc: GREEN },
      { n: "5,2 dgn", l: "gemiddelde doorlooptijd", d: "−18% t.o.v. Q2 2025", dc: GREEN },
      { n: "+42", l: "NPS opdrachtgevers", d: "+5 punten", dc: GREEN },
      { n: "−9%", l: "kosten per dossier", d: "door digitale afhandeling", dc: GREY },
    ];
    const gx = 6.5, gy = 1.75, cw = 3.1, ch = 2.25, gap = 0.22;
    stats.forEach((st, i) => {
      const x = gx + (i % 2) * (cw + gap);
      const y = gy + Math.floor(i / 2) * (ch + gap);
      s.addShape("roundRect", { x, y, w: cw, h: ch, rectRadius: 0.09, fill: { color: CARD } });
      s.addText(st.n, { x: x + 0.25, y: y + 0.28, w: cw - 0.5, h: 0.85, margin: 0, fontFace: HEAD, fontSize: 38, bold: true, color: NAVY });
      s.addText(st.l, { x: x + 0.25, y: y + 1.18, w: cw - 0.5, h: 0.35, margin: 0, fontFace: BODY, fontSize: 12.5, color: "333B49" });
      s.addText(st.d, { x: x + 0.25, y: y + 1.6, w: cw - 0.5, h: 0.35, margin: 0, fontFace: BODY, fontSize: 11.5, bold: true, color: st.dc });
    });
    s.addNotes(
      "Eén slide, vier cijfers — meer heeft de directie in de eerste minuut niet nodig. " +
      "Benadruk de combinatie: méér volume, kórtere doorlooptijd, lágere kosten. " +
      "Kondig hier alvast de drie beslispunten aan, dan weet iedereen waar het gesprek naartoe gaat."
    );
  }

  // ---------- 3 · resultaten per domein ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    slideTitle(s, "Resultaten per domein", "Mobility, Property en Vitality groeien alle drie");

    const domains = [
      { icon: "truck", name: "Mobility", vol: "61.200", pts: ["Volume +7% door twee nieuwe volmacht-opdrachtgevers", "Connect Claims: 52% geautomatiseerd afgehandeld", "Klanttevredenheid 8,4"] },
      { icon: "home", name: "Property", vol: "48.700", pts: ["Volume +5%; piek na junistormen goed opgevangen", "Instant Expertise® nu ook bij inboedelschade", "Doorlooptijd −22%, grootste daling van alle domeinen"] },
      { icon: "heart", name: "Vitality", vol: "18.500", pts: ["Volume +8%; personenschade blijft groeimarkt", "Wachttijd medisch advies loopt op — zie beslispunt 2", "Klanttevredenheid 8,1"] },
    ];
    const cw = 3.87, gap = 0.26, cy = 2.0, chh = 3.95;
    domains.forEach((d, i) => {
      const x = 0.6 + i * (cw + gap);
      s.addShape("roundRect", { x, y: cy, w: cw, h: chh, rectRadius: 0.1, fill: { color: CARD } });
      iconCircle(s, d.icon, x + 0.3, cy + 0.32, 0.72, NAVY);
      s.addText(d.name, { x: x + 1.2, y: cy + 0.36, w: cw - 1.4, h: 0.4, margin: 0, fontFace: HEAD, fontSize: 19, bold: true, color: NAVY });
      s.addText([
        { text: d.vol, options: { fontSize: 26, bold: true, color: NAVY } },
        { text: "  dossiers", options: { fontSize: 12, color: GREY } },
      ], { x: x + 1.2, y: cy + 0.72, w: cw - 1.4, h: 0.5, margin: 0, fontFace: HEAD });
      s.addText(
        d.pts.map((t, j) => ({
          text: t,
          options: { bullet: true, breakLine: j < d.pts.length - 1, paraSpaceAfter: 8 },
        })),
        { x: x + 0.32, y: cy + 1.55, w: cw - 0.64, h: chh - 1.85, margin: 0, fontFace: BODY, fontSize: 12.5, color: "333B49", valign: "top" }
      );
    });
    s.addNotes(
      "Per domein één regel groei, één regel operatie, één regel kwaliteit. " +
      "Bij Vitality bewust het knelpunt benoemen (wachttijd medisch advies) — dat maakt beslispunt 2 straks logisch."
    );
  }

  // ---------- 4 · volume & doorlooptijd (grafieken) ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    slideTitle(s, "Operationele prestaties", "Volume stijgt, doorlooptijd daalt");

    const cats = ["Q3 '25", "Q4 '25", "Q1 '26", "Q2 '26"];
    s.addChart("bar", [
      { name: "Mobility", labels: cats, values: [54.1, 56.8, 58.9, 61.2] },
      { name: "Property", labels: cats, values: [44.9, 47.2, 45.8, 48.7] },
      { name: "Vitality", labels: cats, values: [16.2, 16.9, 17.6, 18.5] },
    ], {
      x: 0.6, y: 1.85, w: 6.0, h: 4.35,
      barDir: "col", barGrouping: "stacked",
      chartColors: [NAVY, "5B79B8", ACCENT],
      showTitle: true, title: "Afgehandelde dossiers per kwartaal (× 1.000)",
      titleFontFace: BODY, titleFontSize: 13, titleColor: NAVY,
      showValue: true, dataLabelPosition: "ctr", dataLabelColor: WHITE,
      dataLabelFontFace: BODY, dataLabelFontSize: 9,
      showLegend: true, legendPos: "b", legendFontFace: BODY, legendFontSize: 11, legendColor: GREY,
      catAxisLabelColor: GREY, catAxisLabelFontFace: BODY, catAxisLabelFontSize: 11,
      valAxisLabelColor: GREY, valAxisLabelFontFace: BODY, valAxisLabelFontSize: 10,
      valGridLine: { color: "E3E9F2", size: 0.5 }, catGridLine: { style: "none" },
    });

    s.addChart("line", [
      { name: "Doorlooptijd", labels: cats, values: [6.8, 6.3, 5.7, 5.2] },
    ], {
      x: 6.95, y: 1.85, w: 5.75, h: 4.35,
      chartColors: [ACCENT], lineSize: 3, lineSmooth: false,
      lineDataSymbol: "circle", lineDataSymbolSize: 8,
      showTitle: true, title: "Gemiddelde doorlooptijd (dagen)",
      titleFontFace: BODY, titleFontSize: 13, titleColor: NAVY,
      showValue: true, dataLabelPosition: "t", dataLabelColor: NAVY,
      dataLabelFontFace: BODY, dataLabelFontSize: 11, dataLabelFormatCode: "0.0",
      showLegend: false,
      catAxisLabelColor: GREY, catAxisLabelFontFace: BODY, catAxisLabelFontSize: 11,
      valAxisLabelColor: GREY, valAxisLabelFontFace: BODY, valAxisLabelFontSize: 10,
      valAxisMinVal: 0, valAxisMaxVal: 8,
      valGridLine: { color: "E3E9F2", size: 0.5 }, catGridLine: { style: "none" },
    });

    s.addText([
      { text: "Takeaway:  ", options: { bold: true, color: NAVY } },
      { text: "vier kwartalen op rij méér dossiers in mínder dagen — de schaalbaarheid van het digitale proces bewijst zich.", options: { color: "333B49" } },
    ], { x: 0.6, y: 6.4, w: 12.1, h: 0.45, margin: 0, fontFace: BODY, fontSize: 13.5 });
    s.addNotes(
      "Laat de twee grafieken samen het verhaal vertellen: links groeit het volume, rechts daalt de doorlooptijd. " +
      "Dat is de kern van het kwartaal. Verwacht de vraag 'houdt die daling aan?' — antwoord: ja, mits AI-triage wordt goedgekeurd (beslispunt 1)."
    );
  }

  // ---------- 5 · klanttevredenheid ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    slideTitle(s, "Klant & kwaliteit", "Opdrachtgevers én verzekerden waarderen het digitale proces");

    // links: donker paneel met NPS
    s.addShape("roundRect", { x: 0.6, y: 1.8, w: 4.35, h: 4.7, rectRadius: 0.1, fill: { color: NAVY_DEEP } });
    iconCircle(s, "smile", 0.95, 2.15, 0.75, ACCENT);
    s.addText("NPS opdrachtgevers", { x: 1.85, y: 2.3, w: 3.0, h: 0.4, margin: 0, fontFace: BODY, fontSize: 13, color: ICE });
    s.addText("+42", { x: 0.95, y: 3.0, w: 3.6, h: 1.2, margin: 0, fontFace: HEAD, fontSize: 64, bold: true, color: WHITE });
    const kwal = [
      "Klanttevredenheid verzekerden: 8,3 (was 8,0)",
      "First-time-fix bij expertise: 87%",
      "Klachtenratio gedaald naar 0,6% van de dossiers",
    ];
    s.addText(
      kwal.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < kwal.length - 1, paraSpaceAfter: 9 } })),
      { x: 0.95, y: 4.35, w: 3.7, h: 1.9, margin: 0, fontFace: BODY, fontSize: 12.5, color: ICE, valign: "top" }
    );

    // rechts: NPS-ontwikkeling
    s.addChart("line", [
      { name: "NPS", labels: ["Q1 '25", "Q2 '25", "Q3 '25", "Q4 '25", "Q1 '26", "Q2 '26"], values: [31, 37, 36, 38, 40, 42] },
    ], {
      x: 5.35, y: 1.85, w: 7.35, h: 4.6,
      chartColors: [NAVY], lineSize: 3,
      lineDataSymbol: "circle", lineDataSymbolSize: 8,
      showTitle: true, title: "NPS-ontwikkeling per kwartaal",
      titleFontFace: BODY, titleFontSize: 13, titleColor: NAVY,
      showValue: true, dataLabelPosition: "t", dataLabelColor: NAVY,
      dataLabelFontFace: BODY, dataLabelFontSize: 11,
      showLegend: false,
      catAxisLabelColor: GREY, catAxisLabelFontFace: BODY, catAxisLabelFontSize: 11,
      valAxisLabelColor: GREY, valAxisLabelFontFace: BODY, valAxisLabelFontSize: 10,
      valAxisMinVal: 0, valAxisMaxVal: 50,
      valGridLine: { color: "E3E9F2", size: 0.5 }, catGridLine: { style: "none" },
    });
    s.addNotes(
      "De dip in Q3 '25 kwam door de zomerpiek — benoem dat zelf voordat ernaar wordt gevraagd. " +
      "De stijging sindsdien loopt gelijk op met de uitrol van Instant Expertise: snelheid ís klanttevredenheid."
    );
  }

  // ---------- 6 · digitalisering / Instant Expertise ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    slideTitle(s, "Digitalisering", "Instant Expertise® wordt de standaard");

    const rows = [
      { icon: "zap", t: "64% adoptie", d: "van de geschikte dossiers wordt volledig digitaal afgehandeld (Q2 2025: 38%)" },
      { icon: "cpu", t: "41% straight-through", d: "geen menselijke tussenkomst nodig; expert alleen bij twijfelgevallen en complexe schade" },
      { icon: "clock", t: "78% binnen 24 uur", d: "van melding tot akkoord op schadebedrag — was 3,1 dagen gemiddeld" },
      { icon: "shield", t: "Fraude-indicatie ingebouwd", d: "automatische signalering; 2,3% van de dossiers doorgezet naar Toedracht & Fraude" },
    ];
    rows.forEach((r, i) => {
      const y = 1.85 + i * 1.15;
      iconCircle(s, r.icon, 0.6, y, 0.7, NAVY);
      s.addText(r.t, { x: 1.55, y: y - 0.02, w: 5.6, h: 0.38, margin: 0, fontFace: BODY, fontSize: 15.5, bold: true, color: NAVY });
      s.addText(r.d, { x: 1.55, y: y + 0.36, w: 5.75, h: 0.62, margin: 0, fontFace: BODY, fontSize: 12, color: "333B49" });
    });

    // rechts: accentpaneel met de volgende stap
    s.addShape("roundRect", { x: 7.75, y: 1.85, w: 4.95, h: 4.55, rectRadius: 0.1, fill: { color: NAVY_DEEP } });
    iconCircle(s, "target", 8.15, 2.25, 0.75, ACCENT);
    s.addText("Volgende stap: AI-triage", { x: 8.15, y: 3.25, w: 4.2, h: 0.45, margin: 0, fontFace: HEAD, fontSize: 19, bold: true, color: WHITE });
    s.addText(
      "Automatische routering van élk nieuw dossier: direct digitaal afhandelen, naar een expert, of naar fraude-onderzoek. Verwachte extra besparing: € 1,8 mln per jaar bij een investering van € 1,2 mln.",
      { x: 8.15, y: 3.78, w: 4.2, h: 1.7, margin: 0, fontFace: BODY, fontSize: 12.5, color: ICE, valign: "top" }
    );
    s.addText("→ Beslispunt 1, slide 9", { x: 8.15, y: 5.75, w: 4.2, h: 0.35, margin: 0, fontFace: BODY, fontSize: 12, bold: true, italic: true, color: ACCENT });
    s.addNotes(
      "Dit is de trotse slide — hier zit het verhaal achter alle eerdere cijfers. " +
      "Het rechterpaneel bouwt de brug naar het investeringsvoorstel: noem de terugverdientijd (minder dan een jaar) hardop."
    );
  }

  // ---------- 7 · risico's ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    slideTitle(s, "Risico's & aandachtspunten", "Drie thema's die sturing van de directie vragen");

    const risks = [
      { icon: "users", t: "Arbeidsmarkt experts", impact: "Uitstroom personenschade-experts (7% in H1); werving blijft achter bij groei Vitality.", mit: "Mitigatie: traineeship uitbreiden, senioren inzetten op alleen complexe dossiers." },
      { icon: "rain", t: "Weersextremen", impact: "Piekbelasting na stormen zet doorlooptijd Property onder druk; juni-piek kostte 0,4 dag.", mit: "Mitigatie: flexibele schil vergroten en piekprotocol met opdrachtgevers afspreken." },
      { icon: "db", t: "Datamigratie legacy", impact: "Migratie van het oude expertisesysteem loopt 6 weken achter op planning.", mit: "Mitigatie: scope bevriezen, go-live verplaatst naar november — geen extra budget nodig." },
    ];
    const cw = 3.87, gap = 0.26, cy = 1.95, chh = 4.15;
    risks.forEach((r, i) => {
      const x = 0.6 + i * (cw + gap);
      s.addShape("roundRect", { x, y: cy, w: cw, h: chh, rectRadius: 0.1, fill: { color: CARD } });
      iconCircle(s, r.icon, x + 0.3, cy + 0.32, 0.72, RED);
      s.addText(r.t, { x: x + 1.2, y: cy + 0.44, w: cw - 1.45, h: 0.75, margin: 0, fontFace: HEAD, fontSize: 16.5, bold: true, color: NAVY });
      s.addText(r.impact, { x: x + 0.32, y: cy + 1.45, w: cw - 0.64, h: 1.15, margin: 0, fontFace: BODY, fontSize: 12.5, color: "333B49", valign: "top" });
      s.addText(r.mit, { x: x + 0.32, y: cy + 2.65, w: cw - 0.64, h: 1.35, margin: 0, fontFace: BODY, fontSize: 12.5, italic: true, color: GREEN, valign: "top" });
    });
    s.addNotes(
      "Gouden regel voor directiepresentaties: nooit een risico noemen zonder mitigatie. " +
      "Elke kaart eindigt daarom groen. De datamigratie is het gevoeligste punt — wees daar het eerlijkst en het concreetst."
    );
  }

  // ---------- 8 · roadmap H2 ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    slideTitle(s, "Vooruitblik", "Roadmap tweede halfjaar 2026");

    const steps = [
      { q: "SEP", t: "AI-triage pilot", d: "Start pilot bij Mobility met twee opdrachtgevers; 5.000 dossiers." },
      { q: "OKT", t: "Instant Expertise® Property", d: "Uitrol naar alle opstal- en inboedeldossiers tot € 15.000." },
      { q: "NOV", t: "Go-live nieuw kernsysteem", d: "Afronding datamigratie; legacy-systeem uit per 1 december." },
      { q: "DEC", t: "Klantportaal opdrachtgevers", d: "Realtime dossierinzicht en stuurinformatie voor verzekeraars." },
    ];
    const y0 = 2.7, cw2 = 2.85, gap2 = 0.21;
    // verbindingslijn
    s.addShape("line", { x: 1.05, y: y0 + 0.35, w: 0.6 + 3 * (cw2 + gap2) + 0.4 - 1.05, h: 0, line: { color: ICE, width: 2.5 } });
    steps.forEach((st, i) => {
      const x = 0.6 + i * (cw2 + gap2);
      s.addShape("ellipse", { x: x + 0.1, y: y0, w: 0.7, h: 0.7, fill: { color: i === 0 ? ACCENT : NAVY } });
      s.addText(String(i + 1), { x: x + 0.1, y: y0, w: 0.7, h: 0.7, margin: 0, align: "center", valign: "middle", fontFace: HEAD, fontSize: 20, bold: true, color: WHITE });
      s.addText(st.q, { x: x + 0.95, y: y0 + 0.14, w: 1.6, h: 0.35, margin: 0, fontFace: BODY, fontSize: 13, bold: true, color: GREY, charSpacing: 2 });
      s.addText(st.t, { x, y: y0 + 1.0, w: cw2, h: 0.75, margin: 0, fontFace: HEAD, fontSize: 15.5, bold: true, color: NAVY });
      s.addText(st.d, { x, y: y0 + 1.75, w: cw2, h: 1.3, margin: 0, fontFace: BODY, fontSize: 12, color: "333B49", valign: "top" });
    });
    s.addText([
      { text: "Doel eind 2026:  ", options: { bold: true, color: NAVY } },
      { text: "75% van alle geschikte dossiers volledig digitaal, doorlooptijd onder de 4,5 dagen.", options: { color: "333B49" } },
    ], { x: 0.6, y: 6.35, w: 12.1, h: 0.45, margin: 0, fontFace: BODY, fontSize: 13.5 });
    s.addNotes(
      "Vier mijlpalen, één per maand — meer detail hoort niet op directieniveau. " +
      "Het amberkleurige bolletje (september) markeert wat er als eerste komt én waarvoor vandaag akkoord nodig is."
    );
  }

  // ---------- 9 · beslispunten ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    slideTitle(s, "Gevraagde besluiten", "Drie beslispunten voor de directie");

    const dec = [
      { t: "Investering AI-triage", d: "€ 1,2 mln eenmalig; verwachte besparing € 1,8 mln per jaar vanaf 2027. Terugverdientijd < 12 maanden.", ask: "Gevraagd: akkoord op investering en start pilot in september." },
      { t: "Capaciteit Vitality", d: "Zes extra medisch adviseurs (4 fte vast, 2 flexibel) om de wachttijd medisch advies terug te brengen van 19 naar 10 werkdagen.", ask: "Gevraagd: akkoord op uitbreiding formatie per 1 oktober." },
      { t: "Go/no-go klantportaal", d: "Ontwikkeling afgerond; live-gang in december vergt commitment van accountteams voor onboarding van de top-10 opdrachtgevers.", ask: "Gevraagd: go-besluit en aanwijzen sponsor vanuit de directie." },
    ];
    dec.forEach((d, i) => {
      const y = 1.8 + i * 1.62;
      s.addShape("roundRect", { x: 0.6, y, w: 12.13, h: 1.45, rectRadius: 0.09, fill: { color: i === 0 ? NAVY_DEEP : CARD } });
      const dark = i === 0;
      s.addShape("ellipse", { x: 0.9, y: y + 0.38, w: 0.68, h: 0.68, fill: { color: dark ? ACCENT : NAVY } });
      s.addText(String(i + 1), { x: 0.9, y: y + 0.38, w: 0.68, h: 0.68, margin: 0, align: "center", valign: "middle", fontFace: HEAD, fontSize: 20, bold: true, color: WHITE });
      s.addText(d.t, { x: 1.85, y: y + 0.16, w: 3.4, h: 1.15, margin: 0, fontFace: HEAD, fontSize: 16.5, bold: true, color: dark ? WHITE : NAVY, valign: "middle" });
      s.addText(d.d, { x: 5.4, y: y + 0.14, w: 4.55, h: 1.2, margin: 0, fontFace: BODY, fontSize: 11.5, color: dark ? ICE : "333B49", valign: "middle" });
      s.addText(d.ask, { x: 10.1, y: y + 0.14, w: 2.45, h: 1.2, margin: 0, fontFace: BODY, fontSize: 11, bold: true, italic: true, color: dark ? ACCENT : GREEN, valign: "middle" });
    });
    s.addNotes(
      "Formuleer elk besluit als een vraag waar 'ja' op kan worden gezegd. " +
      "Beslispunt 1 staat bewust bovenaan en donker uitgelicht: dat is het belangrijkste besluit van vandaag. " +
      "Sluit af met: 'Kunnen we op alle drie de punten vandaag een besluit nemen?'"
    );
  }

  // ---------- 10 · slot ----------
  {
    const s = pres.addSlide();
    s.background = { color: NAVY_DEEP };
    s.addShape("ellipse", { x: -2.4, y: 4.2, w: 6.2, h: 6.2, fill: { color: NAVY, transparency: 40 } });
    s.addShape("ellipse", { x: 11.4, y: -1.8, w: 4.8, h: 4.8, fill: { color: "24356B", transparency: 45 } });
    s.addShape("ellipse", { x: 10.55, y: 1.85, w: 1.1, h: 1.1, fill: { color: ACCENT } });

    s.addText("Vragen & discussie", { x: 0.85, y: 2.5, w: 11.6, h: 1.1, margin: 0, fontFace: HEAD, fontSize: 48, bold: true, color: WHITE });
    s.addText(
      "Méér dossiers, sneller afgehandeld, tegen lagere kosten — met drie besluiten zetten we die lijn door in 2027.",
      { x: 0.85, y: 3.75, w: 9.2, h: 0.9, margin: 0, fontFace: BODY, fontSize: 17, italic: true, color: ICE }
    );
    s.addText("CED  ·  Schade-expertise & Claims Management      |      [naam]@ced.group", {
      x: 0.85, y: 6.55, w: 10.5, h: 0.35, margin: 0, fontFace: BODY, fontSize: 11, color: "8FA3C8",
    });
    s.addNotes(
      "Herhaal de kernboodschap in één zin en geef het woord aan de directie. " +
      "Tip: houd de beslispunten-slide (9) bij de hand om naar terug te schakelen tijdens de discussie."
    );
  }

  await pres.writeFile({ fileName: __dirname + "/CED-directiepresentatie-voorbeeld.pptx" });
  console.log("Klaar: CED-directiepresentatie-voorbeeld.pptx");
})().catch((e) => { console.error(e); process.exit(1); });
