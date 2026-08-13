/**
 * Genereert merk-placeholders (favicons + og-image) met sharp.
 * Puur geometrisch: donker vlak met de blauwe punt (het merkaccent).
 * Vervang deze bestanden door de echte favicons/logo zodra beschikbaar.
 */
import sharp from 'sharp';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const INK = '#0B0B0B';
const BLUE = '#29B0F2';
const CREAM = '#F2EDE3';

function faviconSvg(size) {
  const r = Math.round(size * 0.22);
  const dot = Math.round(size * 0.16);
  const cx = Math.round(size * 0.66);
  const cy = Math.round(size * 0.66);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <rect width="${size}" height="${size}" rx="${r}" fill="${INK}"/>
  <rect x="${Math.round(size * 0.28)}" y="${Math.round(size * 0.26)}" width="${Math.round(size * 0.11)}" height="${Math.round(size * 0.42)}" rx="2" fill="${CREAM}"/>
  <circle cx="${cx}" cy="${cy}" r="${dot}" fill="${BLUE}"/>
</svg>`;
}

function ogSvg(w, h) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  <rect width="${w}" height="${h}" fill="${INK}"/>
  <circle cx="${w * 0.5}" cy="${h * 0.5}" r="${h * 0.22}" fill="none" stroke="${BLUE}" stroke-width="${h * 0.012}" opacity="0.25"/>
  <circle cx="${w * 0.62}" cy="${h * 0.5}" r="${h * 0.05}" fill="${BLUE}"/>
</svg>`;
}

async function write(path, svg) {
  mkdirSync(dirname(path), { recursive: true });
  await sharp(Buffer.from(svg)).png().toFile(path);
  console.log('✓', path);
}

const base = 'public/assets';
await write(`${base}/favicon-32.png`, faviconSvg(32));
await write(`${base}/favicon-64.png`, faviconSvg(64));
await write(`${base}/favicon-180.png`, faviconSvg(180));
await write(`${base}/logo-square.png`, ogSvg(1200, 630));
console.log('Klaar.');
