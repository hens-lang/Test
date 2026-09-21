// Template-laag: bouwt deck.html vanuit content/slides.json.
// Alle teksten komen uit de contentlaag, hier staat alleen layout.
'use strict';

const esc = (s) =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Monoline iconen (Lucide-stijl, 24x24, stroke 1.5)
const ICONS = {
  phone:
    '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
  mail:
    '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  target:
    '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  calendar:
    '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/><path d="m9 16 2 2 4-4"/>',
  building:
    '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4M10 10h4M10 14h4M10 18h4"/>',
  spark: '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
  usercheck:
    '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m16 11 2 2 4-4"/>',
  users:
    '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  listx:
    '<path d="M11 12H3M16 6H3M16 18H3"/><path d="m19 10 4 4m0-4-4 4"/>',
  check: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
  repeat:
    '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
  checkSmall: '<path d="m5 13 4 4L19 7"/>',
};

const icon = (name, cls = '') =>
  `<svg class="ic ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ''}</svg>`;

const logo = () => `<div class="logo">LINK<span class="dot">.</span></div>`;

const footer = (meta, n, total) =>
  `<div class="footer"><span>${esc(meta.footerLeft)}</span><span>${n} / ${total}</span></div>`;

const title = (segs, tag = 'h2') =>
  `<${tag} class="title">${segs
    .map((s) => (s.accent ? `<em class="acc">${esc(s.t)}</em>` : esc(s.t)))
    .join('')}</${tag}>`;

const eyebrow = (t) => `<div class="eyebrow">${esc(t)}</div>`;

// Abstract lijnpatroon voor de cover: knooppunten die verbonden worden (LINK).
function coverArt() {
  const nodes = [
    [1285, 700], [1460, 545], [1665, 620], [1600, 810], [1400, 880],
    [1745, 430], [1830, 740], [1560, 985], [1855, 930],
  ];
  const links = [
    [0, 1], [1, 2], [2, 3], [3, 4], [4, 0], [1, 5], [2, 5], [2, 6],
    [3, 6], [3, 7], [4, 7], [6, 8], [7, 8],
  ];
  const lines = links
    .map(([a, b]) => {
      const [x1, y1] = nodes[a];
      const [x2, y2] = nodes[b];
      return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
    })
    .join('');
  const dots = nodes
    .map(([x, y], i) => `<circle cx="${x}" cy="${y}" r="${i === 2 ? 7 : 4}" class="${i === 2 ? 'nd nd-acc' : 'nd'}"/>`)
    .join('');
  return `<svg class="cover-art" viewBox="0 0 1920 1080" fill="none" stroke="rgba(56,182,255,0.28)" stroke-width="1.5">${lines}${dots}</svg>`;
}

/* ---------- slide-templates ---------- */

function partnerLockup(meta) {
  const p = meta.partner;
  if (!p) return '';
  let inner;
  if (p.logo) {
    const fs = require('fs');
    const path = require('path');
    const file = path.resolve(__dirname, '..', p.logo);
    if (fs.existsSync(file)) {
      const ext = path.extname(file).slice(1).toLowerCase();
      const mime = ext === 'svg' ? 'image/svg+xml' : `image/${ext === 'jpg' ? 'jpeg' : ext}`;
      const b64 = fs.readFileSync(file).toString('base64');
      inner = `<img src="data:${mime};base64,${b64}" alt="${esc(p.name)}">`;
    }
  }
  if (!inner) inner = `<span class="partner-name">${esc(p.name)}</span>`;
  return `
  <div class="partner-lockup">
    <span class="lockup-link">LINK<span class="dot">.</span></span>
    <span class="lockup-x">×</span>
    <span class="partner-chip">${inner}</span>
  </div>`;
}

function slideCover(s, meta) {
  return `
  <div class="glow"></div>
  ${coverArt()}
  <div class="cover-body">
    ${eyebrow(s.eyebrow)}
    ${title(s.title, 'h1')}
    <p class="cover-sub">${esc(s.sub)}</p>
    ${partnerLockup(meta)}
  </div>`;
}

function slideAbout(s) {
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="about-grid">
    <div class="about-text">
      ${s.paragraphs.map((p) => `<p>${esc(p)}</p>`).join('')}
    </div>
    <div class="about-stats">
      ${s.stats
        .map(
          (st) => `
      <div class="card stat-card">
        <div class="stat-value">${esc(st.value)}</div>
        <div class="stat-label">${esc(st.label)}</div>
        <div class="stat-detail">${esc(st.detail)}</div>
      </div>`
        )
        .join('')}
    </div>
  </div>`;
}

function slideServices(s) {
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="cards-4">
    ${s.cards
      .map(
        (c) => `
    <div class="card svc-card${c.highlight ? ' svc-highlight' : ''}">
      <div class="icon-badge">${icon(c.icon)}</div>
      <h3>${esc(c.title)}</h3>
      <p>${esc(c.text)}</p>
    </div>`
      )
      .join('')}
  </div>`;
}

function slideProcess(s) {
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="steps-row">
    ${s.steps
      .map(
        (st, i) => `
    <div class="step">
      <div class="step-track"><div class="step-num">${i + 1}</div>${
          i < s.steps.length - 1 ? '<div class="step-line"></div>' : ''
        }</div>
      <h3>${esc(st.title)}</h3>
      <p>${esc(st.text)}</p>
    </div>`
      )
      .join('')}
  </div>
  <div class="card dark-card deliver">
    <h3>${esc(s.deliverables.title)}</h3>
    <div class="deliver-grid">
      ${s.deliverables.items
        .map((it) => `<div class="deliver-item">${icon('checkSmall', 'ic-acc')}<span>${esc(it)}</span></div>`)
        .join('')}
    </div>
  </div>`;
}

function slideQualification(s) {
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="cards-3">
    ${s.cards
      .map(
        (c) => `
    <div class="card qual-card">
      <div class="icon-badge">${icon(c.icon)}</div>
      <h3>${esc(c.title)}</h3>
      <p>${esc(c.text)}</p>
    </div>`
      )
      .join('')}
  </div>
  <p class="closing">${esc(s.closing)}</p>`;
}

function slideRules(s) {
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="rules-grid">
    ${s.rules
      .map(
        (r) => `
    <div class="rule">
      <div class="rule-check">${icon('checkSmall', 'ic-acc')}</div>
      <div>
        <h3>${esc(r.title)}</h3>
        <p>${esc(r.text)}</p>
      </div>
    </div>`
      )
      .join('')}
  </div>`;
}

function slidePilot(s) {
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="cards-4 pilot-cards">
    ${s.cards
      .map(
        (c) => `
    <div class="card dark-card pilot-card${c.highlight ? ' pilot-highlight' : ''}">
      <div class="pilot-value">${esc(c.value)}</div>
      <div class="pilot-unit">${esc(c.unit)}</div>
      <div class="pilot-label">${esc(c.label)}</div>
    </div>`
      )
      .join('')}
  </div>
  <div class="timeline">
    ${s.timeline
      .map(
        (t) => `
    <div class="tl-seg">
      <div class="tl-track"><div class="tl-dot"></div><div class="tl-bar"></div></div>
      <div class="tl-phase">${esc(t.phase)}</div>
      <div class="tl-period">${esc(t.period)}</div>
      <div class="tl-text">${esc(t.text)}</div>
    </div>`
      )
      .join('')}
  </div>`;
}

function slideNeeds(s) {
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="cards-2x2">
    ${s.cards
      .map(
        (c) => `
    <div class="card need-card">
      <div class="icon-badge">${icon(c.icon)}</div>
      <div>
        <h3>${esc(c.title)}</h3>
        <p>${esc(c.text)}</p>
      </div>
    </div>`
      )
      .join('')}
  </div>`;
}

function slideNext(s) {
  const c = s.contact;
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="next-grid">
    <div class="next-steps">
      ${s.steps
        .map(
          (st, i) => `
      <div class="next-step">
        <div class="step-num">${i + 1}</div>
        <div>
          <h3>${esc(st.title)}</h3>
          <p>${esc(st.text)}</p>
        </div>
      </div>`
        )
        .join('')}
    </div>
    <div class="card dark-card contact-card">
      <div class="contact-name">${esc(c.name)}</div>
      <div class="contact-role">${esc(c.role)}</div>
      <div class="contact-lines">
        <div>${esc(c.email)}</div>
        <div>${esc(c.site)}</div>
        <div>${esc(c.address)}</div>
      </div>
    </div>
  </div>`;
}

function slideOffer(s) {
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="offer-cards">
    ${s.cards
      .map(
        (c, i) => `
    <div class="card dark-card offer-card${c.highlight ? ' offer-highlight' : ''}">
      <div class="num-badge">${i + 1}</div>
      <h3>${esc(c.title)}</h3>
      <p>${esc(c.text)}</p>
    </div>`
      )
      .join('')}
  </div>
  <div class="offer-bar">
    <div class="offer-price">
      <div class="offer-label">${esc(s.bar.label)}</div>
      <div class="offer-amount">${esc(s.bar.price)}</div>
      <div class="offer-note">${esc(s.bar.note)}</div>
    </div>
    <div class="offer-items">
      ${s.bar.items
        .map((it) => `<div class="offer-item">${icon('checkSmall')}<span>${esc(it)}</span></div>`)
        .join('')}
    </div>
  </div>`;
}

function slidePlan(s) {
  return `
  <div class="head">${eyebrow(s.eyebrow)}${title(s.title)}</div>
  <div class="plan-row">
    ${s.steps
      .map(
        (st, i) => `
    <div class="plan-step">
      <div class="step-track"><div class="step-num">${i + 1}</div>${
          i < s.steps.length - 1 ? '<div class="step-line"></div>' : ''
        }</div>
      <h3>${esc(st.title)}</h3>
      <p>${esc(st.text)}</p>
    </div>`
      )
      .join('')}
  </div>
  <p class="closing">${esc(s.closing)}</p>`;
}

const RENDERERS = {
  offer: slideOffer,
  plan: slidePlan,
  cover: slideCover,
  about: slideAbout,
  services: slideServices,
  process: slideProcess,
  qualification: slideQualification,
  rules: slideRules,
  pilot: slidePilot,
  needs: slideNeeds,
  next: slideNext,
};

function renderSlides(data) {
  const total = data.slides.length;
  return data.slides
    .map((s, i) => {
      const body = RENDERERS[s.type](s, data.meta);
      return `<section class="slide theme-${s.theme} slide-${s.type}" id="slide-${i + 1}">
        ${logo()}
        ${body}
        ${footer(data.meta, i + 1, total)}
      </section>`;
    })
    .join('\n');
}

const fontFaces = (fontBase) => `
@font-face { font-family:'Inter'; font-weight:400; font-style:normal; src:url('${fontBase}/@fontsource/inter/files/inter-latin-400-normal.woff2') format('woff2'); }
@font-face { font-family:'Inter'; font-weight:500; font-style:normal; src:url('${fontBase}/@fontsource/inter/files/inter-latin-500-normal.woff2') format('woff2'); }
@font-face { font-family:'Inter'; font-weight:600; font-style:normal; src:url('${fontBase}/@fontsource/inter/files/inter-latin-600-normal.woff2') format('woff2'); }
@font-face { font-family:'Inter'; font-weight:700; font-style:normal; src:url('${fontBase}/@fontsource/inter/files/inter-latin-700-normal.woff2') format('woff2'); }
@font-face { font-family:'Inter'; font-weight:800; font-style:normal; src:url('${fontBase}/@fontsource/inter/files/inter-latin-800-normal.woff2') format('woff2'); }
@font-face { font-family:'Playfair Display'; font-weight:600; font-style:italic; src:url('${fontBase}/@fontsource/playfair-display/files/playfair-display-latin-600-italic.woff2') format('woff2'); }
`;

const BASE_CSS = `
:root {
  --black:#000000; --dark:#141821; --cream:#e9e0cd; --card:#f8f4eb;
  --ink:#1c2230; --muted:#6f6a5c; --accent:#38b6ff;
  --dark-card:#1b2130; --dark-border:rgba(255,255,255,0.09);
  --dark-text:#f2efe6; --dark-muted:#c2c8d2;
  --m:96px;
}
* { margin:0; padding:0; box-sizing:border-box; }
html, body { background:#0a0a0a; }
body { font-family:'Inter', sans-serif; -webkit-font-smoothing:antialiased; }
@page { size:1920px 1080px; margin:0; }

.slide {
  width:1920px; height:1080px; position:relative; overflow:hidden;
  page-break-after:always; break-inside:avoid;
}
.theme-light { background:var(--cream); color:var(--ink); }
.theme-dark  { background:var(--dark);  color:var(--dark-text); }
.slide-cover { background:linear-gradient(155deg,#000000 0%,#0b0e16 55%,#141821 100%); }

/* vaste posities: logo en footer identiek op elke slide */
.logo { position:absolute; top:64px; left:var(--m); font-size:36px; font-weight:800; letter-spacing:-0.02em; }
.logo .dot { color:var(--accent); }
.footer {
  position:absolute; left:var(--m); right:var(--m); bottom:48px;
  display:flex; justify-content:space-between; align-items:baseline;
  font-size:15px; font-weight:500; letter-spacing:0.08em;
}
.theme-light .footer { color:var(--muted); }
.theme-dark .footer { color:#bdc3ce; }

.eyebrow {
  color:var(--accent); text-transform:uppercase; letter-spacing:0.26em;
  font-size:19px; font-weight:600; margin-bottom:28px;
}
.title { font-weight:800; letter-spacing:-0.025em; line-height:1.12; }
h2.title { font-size:64px; max-width:1520px; }
.acc { font-family:'Playfair Display', serif; font-style:italic; font-weight:600; letter-spacing:0; }

.head { position:absolute; top:190px; left:var(--m); right:var(--m); }

.card { background:var(--card); border-radius:16px; }
.dark-card { background:var(--dark-card); border:1px solid var(--dark-border); }

.ic { width:26px; height:26px; }
.ic-acc { color:var(--accent); }
.icon-badge {
  width:60px; height:60px; border-radius:16px; background:rgba(56,182,255,0.13);
  display:flex; align-items:center; justify-content:center; color:var(--accent);
  margin-bottom:28px; flex:none;
}

/* ---------- cover ---------- */
.glow {
  position:absolute; inset:0;
  background:radial-gradient(1000px 760px at 76% 26%, rgba(56,182,255,0.15), transparent 70%);
}
.cover-art { position:absolute; inset:0; width:100%; height:100%; }
.cover-art .nd { fill:#141821; stroke:rgba(56,182,255,0.45); }
.cover-art .nd-acc { fill:var(--accent); stroke:none; }
.cover-body { position:absolute; left:var(--m); top:340px; max-width:1450px; }
h1.title { font-size:104px; letter-spacing:-0.03em; }
.cover-sub { font-size:28px; line-height:1.55; color:#bdc3ce; margin-top:44px; max-width:1050px; font-weight:400; }


.partner-lockup { display:flex; align-items:center; gap:24px; margin-top:56px; }
.lockup-link { font-size:34px; font-weight:800; letter-spacing:-0.02em; color:var(--dark-text); }
.lockup-link .dot { color:var(--accent); }
.lockup-x { font-size:26px; color:#8a90a0; font-weight:500; }
.partner-chip {
  background:var(--card); border-radius:14px; padding:14px 28px;
  display:flex; align-items:center; min-height:64px;
}
.partner-chip img { height:40px; width:auto; max-width:260px; display:block; }
.partner-name { font-size:30px; font-weight:800; letter-spacing:-0.02em; color:var(--ink); }

/* ---------- about ---------- */
.about-grid {
  position:absolute; left:var(--m); right:var(--m); top:420px; bottom:132px;
  display:grid; grid-template-columns:1fr 580px; gap:110px;
}
.about-text p { font-size:27px; line-height:1.66; margin-bottom:40px; max-width:980px; }
.about-stats { display:flex; flex-direction:column; gap:24px; min-height:0; }
.stat-card { padding:36px 44px; flex:1; min-height:0; display:flex; flex-direction:column; justify-content:center; overflow:hidden; }
.stat-value { font-size:68px; font-weight:800; letter-spacing:-0.03em; color:var(--accent); line-height:1; }
.stat-label { font-size:25px; font-weight:700; margin-top:12px; letter-spacing:-0.01em; }
.stat-detail { font-size:19px; line-height:1.5; color:var(--muted); margin-top:10px; }

/* ---------- services / needs ---------- */
.cards-4 {
  position:absolute; left:var(--m); right:var(--m); top:440px; bottom:130px;
  display:grid; grid-template-columns:repeat(4,1fr); gap:24px;
}
.svc-card { padding:44px 40px; display:flex; flex-direction:column; }
.svc-card h3 { font-size:27px; font-weight:700; letter-spacing:-0.015em; margin-bottom:16px; }
.svc-card p { font-size:19px; line-height:1.55; color:var(--muted); }
.svc-highlight { background:var(--black); color:#f2efe6; }
.svc-highlight p { color:#c2c8d2; }
.svc-highlight .icon-badge { background:rgba(56,182,255,0.18); }

/* ---------- process (dark) ---------- */
.steps-row {
  position:absolute; left:var(--m); right:var(--m); top:432px;
  display:grid; grid-template-columns:repeat(4,1fr); gap:40px;
}
.step-track { display:flex; align-items:center; margin-bottom:26px; }
.step-num {
  width:48px; height:48px; border-radius:50%; flex:none;
  border:1.5px solid var(--accent); color:var(--accent);
  display:flex; align-items:center; justify-content:center;
  font-size:21px; font-weight:700;
}
.step-line { flex:1; height:1px; background:rgba(56,182,255,0.35); margin-left:16px; margin-right:-40px; }
.step h3 { font-size:25px; font-weight:700; letter-spacing:-0.015em; margin-bottom:12px; }
.step p { font-size:18px; line-height:1.55; color:var(--dark-muted); }
.deliver { position:absolute; left:var(--m); right:var(--m); bottom:130px; padding:40px 48px; }
.deliver h3 { font-size:23px; font-weight:700; margin-bottom:22px; letter-spacing:-0.01em; }
.deliver-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px 56px; }
.deliver-item { display:flex; align-items:flex-start; gap:14px; font-size:19px; line-height:1.45; color:var(--dark-muted); }
.deliver-item .ic { margin-top:1px; flex:none; width:22px; height:22px; }

/* ---------- qualification ---------- */
.cards-3 {
  position:absolute; left:var(--m); right:var(--m); top:440px;
  display:grid; grid-template-columns:repeat(3,1fr); gap:28px;
}
.qual-card { padding:52px 48px; min-height:390px; }
.qual-card h3 { font-size:32px; font-weight:700; letter-spacing:-0.015em; margin-bottom:18px; }
.qual-card p { font-size:21px; line-height:1.6; color:var(--muted); }
.closing {
  position:absolute; left:var(--m); right:var(--m); bottom:150px;
  font-size:24px; line-height:1.5; font-weight:500; max-width:1400px;
  display:flex; align-items:baseline; gap:18px;
}
.closing::before {
  content:''; width:12px; height:12px; border-radius:50%;
  background:var(--accent); flex:none; align-self:center;
}

/* ---------- rules ---------- */
.rules-grid {
  position:absolute; left:var(--m); right:var(--m); top:430px; bottom:120px;
  display:grid; grid-template-columns:1fr 1fr; column-gap:80px; align-content:start;
}
.rule {
  display:flex; gap:24px; align-items:flex-start;
  padding:34px 0; border-top:1px solid rgba(28,34,48,0.14);
}
.rule:nth-child(1), .rule:nth-child(2) { border-top:none; padding-top:6px; }
.rule-check {
  width:40px; height:40px; border-radius:12px; flex:none; margin-top:2px;
  background:rgba(56,182,255,0.13); display:flex; align-items:center; justify-content:center;
}
.rule-check .ic { width:22px; height:22px; }
.rule h3 { font-size:24px; font-weight:700; letter-spacing:-0.01em; margin-bottom:6px; }
.rule p { font-size:19px; line-height:1.5; color:var(--muted); }

/* ---------- pilot (dark) ---------- */
.pilot-cards { top:430px; bottom:auto; height:330px; }
.pilot-card { padding:40px 36px; display:flex; flex-direction:column; }
.pilot-value { font-size:58px; font-weight:800; letter-spacing:-0.03em; line-height:1; }
.pilot-unit { font-size:19px; font-weight:600; color:var(--accent); text-transform:uppercase; letter-spacing:0.1em; margin-top:14px; }
.pilot-label { font-size:18px; line-height:1.5; color:var(--dark-muted); margin-top:auto; padding-top:18px; }
.pilot-highlight { border:1.5px solid rgba(56,182,255,0.65); box-shadow:0 0 60px rgba(56,182,255,0.12); }
.pilot-highlight .pilot-value { color:var(--accent); }
.timeline {
  position:absolute; left:var(--m); right:var(--m); bottom:128px;
  display:grid; grid-template-columns:repeat(4,1fr);
}
.tl-track { display:flex; align-items:center; margin-bottom:20px; }
.tl-dot { width:14px; height:14px; border-radius:50%; background:var(--accent); flex:none; }
.tl-bar { flex:1; height:1px; background:rgba(56,182,255,0.3); }
.tl-seg:last-child .tl-bar { background:none; }
.tl-phase { font-size:21px; font-weight:700; letter-spacing:-0.01em; }
.tl-period { font-size:15px; font-weight:600; color:var(--accent); text-transform:uppercase; letter-spacing:0.12em; margin-top:6px; }
.tl-text { font-size:17px; line-height:1.45; color:var(--dark-muted); margin-top:8px; padding-right:40px; }

/* ---------- needs (2x2) ---------- */
.cards-2x2 {
  position:absolute; left:var(--m); right:var(--m); top:440px; bottom:130px;
  display:grid; grid-template-columns:1fr 1fr; gap:28px;
}
.need-card { padding:48px 52px; display:flex; gap:36px; align-items:flex-start; }
.need-card .icon-badge { margin-bottom:0; }
.need-card h3 { font-size:29px; font-weight:700; letter-spacing:-0.015em; margin-bottom:12px; }
.need-card p { font-size:21px; line-height:1.55; color:var(--muted); max-width:640px; }

/* ---------- plan (licht stappenpad) ---------- */
.plan-row {
  position:absolute; left:var(--m); right:var(--m); top:460px;
  display:grid; grid-template-columns:repeat(3,1fr); gap:56px;
}
.plan-row .step-line { margin-right:-56px; background:rgba(56,182,255,0.45); }
.plan-step h3 { font-size:30px; font-weight:700; letter-spacing:-0.015em; margin-bottom:14px; }
.plan-step p { font-size:21px; line-height:1.6; color:var(--muted); max-width:480px; }

/* ---------- offer (dark) ---------- */
.offer-cards {
  position:absolute; left:var(--m); right:var(--m); top:388px; height:372px;
  display:grid; grid-template-columns:repeat(4,1fr); gap:24px;
}
.offer-card { padding:36px 34px; display:flex; flex-direction:column; }
.num-badge {
  width:46px; height:46px; border-radius:50%; flex:none;
  border:1.5px solid var(--accent); color:var(--accent);
  display:flex; align-items:center; justify-content:center;
  font-size:20px; font-weight:700; margin-bottom:24px;
}
.offer-card h3 { font-size:23px; font-weight:700; letter-spacing:-0.015em; margin-bottom:12px; }
.offer-card p { font-size:17.5px; line-height:1.5; color:var(--dark-muted); }
.offer-highlight { border:1.5px solid rgba(56,182,255,0.65); box-shadow:0 0 60px rgba(56,182,255,0.12); }
.offer-highlight h3 { color:var(--accent); }
.offer-bar {
  position:absolute; left:var(--m); right:var(--m); bottom:118px;
  background:var(--accent); border-radius:16px; color:#0d1420;
  display:flex; align-items:center; gap:56px; padding:34px 48px;
}
.offer-price { flex:none; width:300px; }
.offer-label { font-size:15px; font-weight:700; text-transform:uppercase; letter-spacing:0.22em; opacity:0.75; }
.offer-amount { font-size:58px; font-weight:800; letter-spacing:-0.03em; line-height:1.05; margin-top:6px; }
.offer-note { font-size:16px; font-weight:600; margin-top:6px; opacity:0.75; }
.offer-items {
  flex:1; display:grid; grid-template-columns:1fr 1fr; gap:14px 40px;
  border-left:1.5px solid rgba(13,20,32,0.25); padding-left:56px;
}
.offer-item { display:flex; align-items:flex-start; gap:12px; font-size:18px; font-weight:600; line-height:1.35; }
.offer-item .ic { width:21px; height:21px; margin-top:2px; flex:none; }

/* ---------- next (dark) ---------- */
.next-grid {
  position:absolute; left:var(--m); right:var(--m); top:460px;
  display:grid; grid-template-columns:1fr 620px; gap:110px;
}
.next-steps { display:flex; flex-direction:column; gap:56px; }
.next-step { display:flex; gap:32px; align-items:flex-start; }
.next-step h3 { font-size:29px; font-weight:700; letter-spacing:-0.015em; margin-bottom:10px; }
.next-step p { font-size:22px; line-height:1.5; color:var(--dark-muted); max-width:760px; }
.contact-card { padding:60px 56px; }
.contact-name { font-size:40px; font-weight:800; letter-spacing:-0.02em; }
.contact-role { font-size:21px; color:var(--accent); font-weight:600; margin-top:8px; }
.contact-lines { margin-top:40px; display:flex; flex-direction:column; gap:16px; }
.contact-lines div { font-size:22px; color:var(--dark-muted); }
`;

function buildHtml(data, { fontBase = '../node_modules' } = {}) {
  return `<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>${esc(data.meta.title)}</title>
<style>
${fontFaces(fontBase)}
${BASE_CSS}
</style>
</head>
<body>
${renderSlides(data)}
</body>
</html>`;
}

module.exports = { buildHtml, renderSlides, BASE_CSS, ICONS };
