// Bouwt de PPTX vanuit content/slides.json met pptxgenjs.
// Zelfde teksten en opbouw als de PDF, als echte bewerkbare slides.
'use strict';

const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');
const sharp = require('sharp');
const { ICONS } = require('./template');

const ROOT = path.resolve(__dirname, '..');
const contentFile = process.argv[2] || 'slides.json';
const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'content', contentFile), 'utf8'));

// px (1920x1080) naar inch (13.333x7.5)
const F = 13.3333 / 1920;
const p = (v) => v * F;

const C = {
  black: '000000',
  dark: '141821',
  cream: 'E9E0CD',
  card: 'F8F4EB',
  ink: '1C2230',
  muted: '6F6A5C',
  accent: '38B6FF',
  darkCard: '1B2130',
  darkBorder: '3A4152',
  darkText: 'F2EFE6',
  darkMuted: 'C2C8D2',
  badgeLight: 'DDEBF3',
  badgeDark: '203C55',
};

const SANS = 'Arial';
const SERIF = 'Georgia';
const RADIUS = p(16);

async function iconPng(name, color) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${ICONS[name]}</svg>`;
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return 'image/png;base64,' + buf.toString('base64');
}

function titleRuns(segs, size) {
  return segs.map((s) =>
    s.accent
      ? { text: s.t, options: { fontFace: SERIF, italic: true, bold: false, fontSize: size - 2 } }
      : { text: s.t, options: { fontFace: SANS, bold: true, fontSize: size } }
  );
}

function addChrome(slide, theme, idx, total) {
  const inkOrLight = theme === 'dark' ? C.darkText : C.ink;
  slide.addText(
    [
      { text: 'LINK', options: { color: inkOrLight } },
      { text: '.', options: { color: C.accent } },
    ],
    { x: p(94), y: p(58), w: p(300), h: p(52), isTextBox: true, margin: 0, fontFace: SANS, bold: true, fontSize: 18, align: 'left', valign: 'middle' }
  );
  const footColor = theme === 'dark' ? 'BDC3CE' : C.muted;
  slide.addText(data.meta.footerLeft, {
    x: p(96), y: p(1005), w: p(900), h: p(36), isTextBox: true, margin: 0,
    fontFace: SANS, bold: true, fontSize: 7.5, color: footColor, charSpacing: 1, align: 'left', valign: 'middle',
  });
  slide.addText(`${idx} / ${total}`, {
    x: p(1524), y: p(1005), w: p(300), h: p(36), isTextBox: true, margin: 0,
    fontFace: SANS, bold: true, fontSize: 7.5, color: footColor, charSpacing: 1, align: 'right', valign: 'middle',
  });
}

function addEyebrow(slide, text, y = 190) {
  slide.addText(text.toUpperCase(), {
    x: p(96), y: p(y), w: p(1600), h: p(34), isTextBox: true, margin: 0,
    fontFace: SANS, bold: true, fontSize: 9.5, color: C.accent, charSpacing: 4, align: 'left', valign: 'middle',
  });
}

function addTitle(slide, segs, theme, y = 238, size = 32, h = 180) {
  slide.addText(titleRuns(segs, size), {
    x: p(96), y: p(y), w: p(1728), h: p(h), isTextBox: true, margin: 0,
    color: theme === 'dark' ? C.darkText : C.ink, align: 'left', valign: 'top',
    lineSpacingMultiple: 1.08,
  });
}

function card(slide, x, y, w, h, fill, line) {
  const opts = { x: p(x), y: p(y), w: p(w), h: p(h), fill: { color: fill }, rectRadius: RADIUS };
  if (line) opts.line = line;
  else opts.line = { type: 'none' };
  slide.addShape('roundRect', opts);
}

async function main() {
  const icons = {};
  const names = Object.keys(ICONS);
  for (const n of names) {
    icons[n] = await iconPng(n, '#38b6ff');
  }
  const checkWhite = await iconPng('checkSmall', '#38b6ff');
  const checkDark = await iconPng('checkSmall', '#0d1420');

  const pres = new pptxgen();
  pres.defineLayout({ name: 'WIDE', width: 13.3333, height: 7.5 });
  pres.layout = 'WIDE';
  pres.author = 'LINK.';
  pres.title = data.meta.title;

  const total = data.slides.length;

  for (let i = 0; i < total; i++) {
    const s = data.slides[i];
    const slide = pres.addSlide();
    const dark = s.theme === 'dark';
    slide.background = { color: s.type === 'cover' ? '070A10' : dark ? C.dark : C.cream };

    if (s.type === 'cover') {
      // abstract lijnpatroon rechtsonder
      const nodes = [
        [1285, 700], [1460, 545], [1665, 620], [1600, 810], [1400, 880],
        [1745, 430], [1830, 740], [1560, 985], [1855, 930],
      ];
      const links = [
        [0, 1], [1, 2], [2, 3], [3, 4], [4, 0], [1, 5], [2, 5], [2, 6],
        [3, 6], [3, 7], [4, 7], [6, 8], [7, 8],
      ];
      for (const [a, b] of links) {
        const [x1, y1] = nodes[a];
        const [x2, y2] = nodes[b];
        slide.addShape('line', {
          x: p(Math.min(x1, x2)), y: p(Math.min(y1, y2)),
          w: p(Math.abs(x2 - x1)), h: p(Math.abs(y2 - y1)),
          flipH: (x2 - x1) * (y2 - y1) < 0,
          line: { color: C.accent, width: 0.75, transparency: 70 },
        });
      }
      nodes.forEach(([x, y], n) => {
        const r = n === 2 ? 7 : 4;
        slide.addShape('ellipse', {
          x: p(x - r), y: p(y - r), w: p(2 * r), h: p(2 * r),
          fill: { color: n === 2 ? C.accent : '141821' },
          line: n === 2 ? { type: 'none' } : { color: C.accent, width: 0.75, transparency: 50 },
        });
      });
      addChrome(slide, s.theme, i + 1, total);
      addEyebrow(slide, s.eyebrow, 336);
      slide.addText(titleRuns(s.title, 52), {
        x: p(96), y: p(396), w: p(1360), h: p(320), isTextBox: true, margin: 0,
        color: C.darkText, align: 'left', valign: 'top', lineSpacingMultiple: 1.05,
      });
      slide.addText(s.sub, {
        x: p(96), y: p(742), w: p(1050), h: p(120), isTextBox: true, margin: 0,
        fontFace: SANS, fontSize: 14, color: 'BDC3CE', lineSpacingMultiple: 1.35, valign: 'top',
      });
      continue;
    }

    addChrome(slide, s.theme, i + 1, total);
    addEyebrow(slide, s.eyebrow);
    addTitle(slide, s.title, s.theme);

    if (s.type === 'about') {
      slide.addText(
        s.paragraphs.map((t, n) => ({
          text: t,
          options: { breakLine: true, paraSpaceAfter: n < s.paragraphs.length - 1 ? 18 : 0 },
        })),
        {
          x: p(96), y: p(424), w: p(960), h: p(500), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 13.5, color: C.ink, lineSpacingMultiple: 1.42, valign: 'top',
        }
      );
      const sx = 1244, sw = 580;
      s.stats.forEach((st, n) => {
        const sy = 420 + n * 268;
        card(slide, sx, sy, sw, 244, C.card);
        slide.addText(st.value, {
          x: p(sx + 44), y: p(sy + 30), w: p(sw - 88), h: p(74), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 34, color: C.accent, valign: 'middle',
        });
        slide.addText(st.label, {
          x: p(sx + 44), y: p(sy + 108), w: p(sw - 88), h: p(38), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 12.5, color: C.ink, valign: 'middle',
        });
        slide.addText(st.detail, {
          x: p(sx + 44), y: p(sy + 150), w: p(sw - 88), h: p(80), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 9.5, color: C.muted, lineSpacingMultiple: 1.3, valign: 'top',
        });
      });
    }

    if (s.type === 'services') {
      const w = 414, gap = 24, y = 440, h = 510;
      s.cards.forEach((c, n) => {
        const x = 96 + n * (w + gap);
        const hl = !!c.highlight;
        card(slide, x, y, w, h, hl ? C.black : C.card);
        slide.addShape('roundRect', {
          x: p(x + 40), y: p(y + 44), w: p(60), h: p(60), rectRadius: p(14),
          fill: { color: hl ? C.badgeDark : C.badgeLight }, line: { type: 'none' },
        });
        slide.addImage({ data: icons[c.icon], x: p(x + 55), y: p(y + 59), w: p(30), h: p(30) });
        slide.addText(c.title, {
          x: p(x + 40), y: p(y + 132), w: p(w - 80), h: p(84), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 13.5, color: hl ? 'FFFFFF' : C.ink, valign: 'top', lineSpacingMultiple: 1.15,
        });
        slide.addText(c.text, {
          x: p(x + 40), y: p(y + 222), w: p(w - 80), h: p(250), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 9.5, color: hl ? C.darkMuted : C.muted, lineSpacingMultiple: 1.35, valign: 'top',
        });
      });
    }

    if (s.type === 'process') {
      const colW = 402, gap = 40, y = 432;
      s.steps.forEach((st, n) => {
        const x = 96 + n * (colW + gap);
        slide.addShape('ellipse', {
          x: p(x), y: p(y), w: p(48), h: p(48),
          fill: { type: 'none' }, line: { color: C.accent, width: 1.2 },
        });
        slide.addText(String(n + 1), {
          x: p(x), y: p(y), w: p(48), h: p(48), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 10.5, color: C.accent, align: 'center', valign: 'middle',
        });
        if (n < s.steps.length - 1) {
          slide.addShape('line', {
            x: p(x + 64), y: p(y + 24), w: p(colW + gap - 72), h: 0,
            line: { color: C.accent, width: 0.75, transparency: 60 },
          });
        }
        slide.addText(st.title, {
          x: p(x), y: p(y + 74), w: p(colW), h: p(40), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 12.5, color: C.darkText, valign: 'middle',
        });
        slide.addText(st.text, {
          x: p(x), y: p(y + 122), w: p(colW), h: p(180), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 9, color: C.darkMuted, lineSpacingMultiple: 1.35, valign: 'top',
        });
      });
      const dy = 742, dh = 208;
      card(slide, 96, dy, 1728, dh, C.darkCard, { color: C.darkBorder, width: 0.75 });
      slide.addText(s.deliverables.title, {
        x: p(144), y: p(dy + 34), w: p(800), h: p(36), isTextBox: true, margin: 0,
        fontFace: SANS, bold: true, fontSize: 11.5, color: C.darkText, valign: 'middle',
      });
      s.deliverables.items.forEach((it, n) => {
        const ix = 144 + (n % 2) * 864;
        const iy = dy + 92 + Math.floor(n / 2) * 48;
        slide.addImage({ data: checkWhite, x: p(ix), y: p(iy + 3), w: p(22), h: p(22) });
        slide.addText(it, {
          x: p(ix + 36), y: p(iy), w: p(790), h: p(40), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 9.5, color: C.darkMuted, valign: 'middle',
        });
      });
    }

    if (s.type === 'qualification') {
      const w = 557, gap = 28, y = 440, h = 390;
      s.cards.forEach((c, n) => {
        const x = 96 + n * (w + gap);
        card(slide, x, y, w, h, C.card);
        slide.addShape('roundRect', {
          x: p(x + 48), y: p(y + 52), w: p(60), h: p(60), rectRadius: p(14),
          fill: { color: C.badgeLight }, line: { type: 'none' },
        });
        slide.addImage({ data: icons[c.icon], x: p(x + 63), y: p(y + 67), w: p(30), h: p(30) });
        slide.addText(c.title, {
          x: p(x + 48), y: p(y + 144), w: p(w - 96), h: p(48), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 16, color: C.ink, valign: 'middle',
        });
        slide.addText(c.text, {
          x: p(x + 48), y: p(y + 204), w: p(w - 96), h: p(150), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 10.5, color: C.muted, lineSpacingMultiple: 1.35, valign: 'top',
        });
      });
      slide.addShape('ellipse', {
        x: p(96), y: p(922), w: p(12), h: p(12), fill: { color: C.accent }, line: { type: 'none' },
      });
      slide.addText(s.closing, {
        x: p(126), y: p(900), w: p(1560), h: p(56), isTextBox: true, margin: 0,
        fontFace: SANS, bold: true, fontSize: 12, color: C.ink, valign: 'middle',
      });
    }

    if (s.type === 'rules') {
      const colW = 824, colGap = 80;
      const rows = [440, 552, 664, 776];
      s.rules.forEach((r, n) => {
        const x = 96 + (n % 2) * (colW + colGap);
        const y = rows[Math.floor(n / 2)];
        if (Math.floor(n / 2) > 0) {
          slide.addShape('line', {
            x: p(x), y: p(y - 12), w: p(colW), h: 0,
            line: { color: 'C9C2B2', width: 0.5 },
          });
        }
        slide.addShape('roundRect', {
          x: p(x), y: p(y + 4), w: p(40), h: p(40), rectRadius: p(10),
          fill: { color: C.badgeLight }, line: { type: 'none' },
        });
        slide.addImage({ data: checkWhite, x: p(x + 9), y: p(y + 13), w: p(22), h: p(22) });
        slide.addText(r.title, {
          x: p(x + 64), y: p(y), w: p(colW - 64), h: p(36), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 12, color: C.ink, valign: 'middle',
        });
        slide.addText(r.text, {
          x: p(x + 64), y: p(y + 38), w: p(colW - 64), h: p(56), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 9.5, color: C.muted, lineSpacingMultiple: 1.3, valign: 'top',
        });
      });
    }

    if (s.type === 'pilot') {
      const w = 414, gap = 24, y = 430, h = 330;
      s.cards.forEach((c, n) => {
        const x = 96 + n * (w + gap);
        const hl = !!c.highlight;
        card(slide, x, y, w, h, C.darkCard, hl ? { color: C.accent, width: 1.2 } : { color: C.darkBorder, width: 0.75 });
        slide.addText(c.value, {
          x: p(x + 36), y: p(y + 36), w: p(w - 72), h: p(64), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 29, color: hl ? C.accent : C.darkText, valign: 'middle',
        });
        slide.addText(c.unit.toUpperCase(), {
          x: p(x + 36), y: p(y + 112), w: p(w - 72), h: p(58), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 9.5, color: C.accent, charSpacing: 1.5, lineSpacingMultiple: 1.2, valign: 'top',
        });
        slide.addText(c.label, {
          x: p(x + 36), y: p(y + 196), w: p(w - 72), h: p(104), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 9, color: C.darkMuted, lineSpacingMultiple: 1.3, valign: 'bottom',
        });
      });
      const tw = 432, ty = 822;
      s.timeline.forEach((t, n) => {
        const x = 96 + n * tw;
        slide.addShape('ellipse', {
          x: p(x), y: p(ty), w: p(14), h: p(14), fill: { color: C.accent }, line: { type: 'none' },
        });
        if (n < s.timeline.length - 1) {
          slide.addShape('line', {
            x: p(x + 22), y: p(ty + 7), w: p(tw - 30), h: 0,
            line: { color: C.accent, width: 0.75, transparency: 65 },
          });
        }
        slide.addText(t.phase, {
          x: p(x), y: p(ty + 34), w: p(tw - 40), h: p(34), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 10.5, color: C.darkText, valign: 'middle',
        });
        slide.addText(t.period.toUpperCase(), {
          x: p(x), y: p(ty + 70), w: p(tw - 40), h: p(26), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 7.5, color: C.accent, charSpacing: 1.5, valign: 'middle',
        });
        slide.addText(t.text, {
          x: p(x), y: p(ty + 100), w: p(tw - 40), h: p(60), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 8.5, color: C.darkMuted, lineSpacingMultiple: 1.25, valign: 'top',
        });
      });
    }

    if (s.type === 'needs') {
      const w = 850, gap = 28, y0 = 440, h = 241;
      s.cards.forEach((c, n) => {
        const x = 96 + (n % 2) * (w + gap);
        const y = y0 + Math.floor(n / 2) * (h + gap);
        card(slide, x, y, w, h, C.card);
        slide.addShape('roundRect', {
          x: p(x + 52), y: p(y + 48), w: p(60), h: p(60), rectRadius: p(14),
          fill: { color: C.badgeLight }, line: { type: 'none' },
        });
        slide.addImage({ data: icons[c.icon], x: p(x + 67), y: p(y + 63), w: p(30), h: p(30) });
        slide.addText(c.title, {
          x: p(x + 148), y: p(y + 44), w: p(w - 200), h: p(44), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 14.5, color: C.ink, valign: 'middle',
        });
        slide.addText(c.text, {
          x: p(x + 148), y: p(y + 96), w: p(w - 210), h: p(110), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 10.5, color: C.muted, lineSpacingMultiple: 1.35, valign: 'top',
        });
      });
    }

    if (s.type === 'plan') {
      const colW = 545, gap = 56, y = 460;
      s.steps.forEach((st, n) => {
        const x = 96 + n * (colW + gap);
        slide.addShape('ellipse', {
          x: p(x), y: p(y), w: p(48), h: p(48),
          fill: { type: 'none' }, line: { color: C.accent, width: 1.2 },
        });
        slide.addText(String(n + 1), {
          x: p(x), y: p(y), w: p(48), h: p(48), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 10.5, color: C.accent, align: 'center', valign: 'middle',
        });
        if (n < s.steps.length - 1) {
          slide.addShape('line', {
            x: p(x + 64), y: p(y + 24), w: p(colW + gap - 72), h: 0,
            line: { color: C.accent, width: 0.75, transparency: 45 },
          });
        }
        slide.addText(st.title, {
          x: p(x), y: p(y + 74), w: p(colW - 60), h: p(44), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 15, color: C.ink, valign: 'middle',
        });
        slide.addText(st.text, {
          x: p(x), y: p(y + 128), w: p(colW - 60), h: p(220), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 10.5, color: C.muted, lineSpacingMultiple: 1.35, valign: 'top',
        });
      });
      slide.addShape('ellipse', {
        x: p(96), y: p(922), w: p(12), h: p(12), fill: { color: C.accent }, line: { type: 'none' },
      });
      slide.addText(s.closing, {
        x: p(126), y: p(900), w: p(1560), h: p(56), isTextBox: true, margin: 0,
        fontFace: SANS, bold: true, fontSize: 12, color: C.ink, valign: 'middle',
      });
    }

    if (s.type === 'offer') {
      const w = 414, gap = 24, y = 388, h = 372;
      const darkInk = '0D1420';
      s.cards.forEach((c, n) => {
        const x = 96 + n * (w + gap);
        const hl = !!c.highlight;
        card(slide, x, y, w, h, C.darkCard, hl ? { color: C.accent, width: 1.2 } : { color: C.darkBorder, width: 0.75 });
        slide.addShape('ellipse', {
          x: p(x + 34), y: p(y + 36), w: p(46), h: p(46),
          fill: { type: 'none' }, line: { color: C.accent, width: 1.2 },
        });
        slide.addText(String(n + 1), {
          x: p(x + 34), y: p(y + 36), w: p(46), h: p(46), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 10, color: C.accent, align: 'center', valign: 'middle',
        });
        slide.addText(c.title, {
          x: p(x + 34), y: p(y + 106), w: p(w - 68), h: p(64), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 11.5, color: hl ? C.accent : C.darkText, valign: 'top', lineSpacingMultiple: 1.15,
        });
        slide.addText(c.text, {
          x: p(x + 34), y: p(y + 178), w: p(w - 68), h: p(170), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 8.75, color: C.darkMuted, lineSpacingMultiple: 1.3, valign: 'top',
        });
      });
      // prijsbalk
      const by = 800, bh = 162;
      slide.addShape('roundRect', {
        x: p(96), y: p(by), w: p(1728), h: p(bh), rectRadius: RADIUS,
        fill: { color: C.accent }, line: { type: 'none' },
      });
      slide.addText(s.bar.label.toUpperCase(), {
        x: p(144), y: p(by + 26), w: p(300), h: p(26), isTextBox: true, margin: 0,
        fontFace: SANS, bold: true, fontSize: 8, color: darkInk, charSpacing: 2, valign: 'middle',
      });
      slide.addText(s.bar.price, {
        x: p(144), y: p(by + 52), w: p(300), h: p(64), isTextBox: true, margin: 0,
        fontFace: SANS, bold: true, fontSize: 29, color: darkInk, valign: 'middle',
      });
      slide.addText(s.bar.note, {
        x: p(144), y: p(by + 118), w: p(320), h: p(26), isTextBox: true, margin: 0,
        fontFace: SANS, bold: true, fontSize: 8, color: darkInk, valign: 'middle',
      });
      slide.addShape('line', {
        x: p(500), y: p(by + 28), w: 0, h: p(bh - 56),
        line: { color: darkInk, width: 0.75, transparency: 60 },
      });
      s.bar.items.forEach((it, n) => {
        const ix = 556 + (n % 2) * 600;
        const iy = by + 26 + Math.floor(n / 2) * 40;
        slide.addImage({ data: checkDark, x: p(ix), y: p(iy + 5), w: p(20), h: p(20) });
        slide.addText(it, {
          x: p(ix + 32), y: p(iy), w: p(560), h: p(34), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 9, color: darkInk, valign: 'middle',
        });
      });
    }

    if (s.type === 'next') {
      s.steps.forEach((st, n) => {
        const y = 460 + n * 140;
        slide.addShape('ellipse', {
          x: p(96), y: p(y), w: p(48), h: p(48),
          fill: { type: 'none' }, line: { color: C.accent, width: 1.2 },
        });
        slide.addText(String(n + 1), {
          x: p(96), y: p(y), w: p(48), h: p(48), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 10.5, color: C.accent, align: 'center', valign: 'middle',
        });
        slide.addText(st.title, {
          x: p(176), y: p(y - 2), w: p(860), h: p(40), isTextBox: true, margin: 0,
          fontFace: SANS, bold: true, fontSize: 14.5, color: C.darkText, valign: 'middle',
        });
        slide.addText(st.text, {
          x: p(176), y: p(y + 44), w: p(860), h: p(70), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 11, color: C.darkMuted, lineSpacingMultiple: 1.3, valign: 'top',
        });
      });
      const cx = 1204, cy = 460, cw = 620, ch = 420;
      card(slide, cx, cy, cw, ch, C.darkCard, { color: C.darkBorder, width: 0.75 });
      const cc = s.contact;
      slide.addText(cc.name, {
        x: p(cx + 56), y: p(cy + 52), w: p(cw - 112), h: p(56), isTextBox: true, margin: 0,
        fontFace: SANS, bold: true, fontSize: 20, color: C.darkText, valign: 'middle',
      });
      slide.addText(cc.role, {
        x: p(cx + 56), y: p(cy + 114), w: p(cw - 112), h: p(34), isTextBox: true, margin: 0,
        fontFace: SANS, bold: true, fontSize: 10.5, color: C.accent, valign: 'middle',
      });
      const lines = [cc.email, cc.site, cc.address];
      lines.forEach((ln, n) => {
        slide.addText(ln, {
          x: p(cx + 56), y: p(cy + 196 + n * 56), w: p(cw - 112), h: p(40), isTextBox: true, margin: 0,
          fontFace: SANS, fontSize: 11, color: C.darkMuted, valign: 'middle',
        });
      });
    }
  }

  const out = path.join(ROOT, 'output', `${data.meta.title}.pptx`);
  await pres.writeFile({ fileName: out });
  console.log('PPTX geschreven:', out);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
