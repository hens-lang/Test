// Rendert deck.html naar PDF en PNG-previews met Playwright,
// en bouwt de contact sheet met sharp.
'use strict';

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const sharp = require('sharp');
const { buildHtml } = require('./template');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'output');
const PREVIEW = path.join(OUT, 'preview');
const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'content', 'slides.json'), 'utf8'));

async function main() {
  fs.mkdirSync(PREVIEW, { recursive: true });
  const htmlPath = path.join(ROOT, 'build', 'deck.html');
  fs.writeFileSync(htmlPath, buildHtml(data));

  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + htmlPath);
  await page.evaluate(() => document.fonts.ready);

  // Overloopcontrole: geen enkele slide mag content buiten 1920x1080 hebben.
  const overflow = await page.evaluate(() => {
    const bad = [];
    document.querySelectorAll('.slide').forEach((slide, i) => {
      const sr = slide.getBoundingClientRect();
      slide.querySelectorAll('*').forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return;
        if (el.closest('.cover-art')) return; // decoratief, mag doorlopen
        if (
          r.right > sr.right + 1 || r.bottom > sr.bottom + 1 ||
          r.left < sr.left - 1 || r.top < sr.top - 1
        ) {
          bad.push(`slide ${i + 1}: <${el.tagName.toLowerCase()} class="${el.className}"> ` +
            `(${Math.round(r.left - sr.left)},${Math.round(r.top - sr.top)}) ` +
            `${Math.round(r.width)}x${Math.round(r.height)}`);
        }
      });
    });
    return bad;
  });
  if (overflow.length) {
    console.log('OVERFLOW WARNINGS:');
    overflow.forEach((w) => console.log('  ' + w));
  } else {
    console.log('Geen overloop buiten de slides.');
  }

  // PDF: elke slide exact één pagina, tekst selecteerbaar.
  await page.pdf({
    path: path.join(OUT, `${data.meta.title}.pdf`),
    preferCSSPageSize: true,
    printBackground: true,
  });
  console.log('PDF geschreven.');

  // PNG per slide
  const slideCount = data.slides.length;
  const pngs = [];
  for (let i = 1; i <= slideCount; i++) {
    const el = page.locator(`#slide-${i}`);
    const file = path.join(PREVIEW, `slide-${String(i).padStart(2, '0')}.png`);
    await el.screenshot({ path: file });
    pngs.push(file);
  }
  console.log(`${slideCount} PNG-previews geschreven.`);
  await browser.close();

  // Contact sheet: 3x3 grid
  const tw = 600, th = 338, gap = 16;
  const cols = 3, rows = Math.ceil(slideCount / cols);
  const W = cols * tw + (cols + 1) * gap;
  const H = rows * th + (rows + 1) * gap;
  const composites = [];
  for (let i = 0; i < pngs.length; i++) {
    const buf = await sharp(pngs[i]).resize(tw, th).png().toBuffer();
    composites.push({
      input: buf,
      left: gap + (i % cols) * (tw + gap),
      top: gap + Math.floor(i / cols) * (th + gap),
    });
  }
  await sharp({
    create: { width: W, height: H, channels: 3, background: { r: 234, g: 231, b: 224 } },
  })
    .composite(composites)
    .png()
    .toFile(path.join(PREVIEW, 'overview.png'));
  console.log('Contact sheet geschreven.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
