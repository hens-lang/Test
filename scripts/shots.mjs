import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const OUT = '/tmp/claude-0/-home-user-Test/141e8455-9ea1-5f45-a6cd-8315513f84f5/scratchpad/shots';
mkdirSync(OUT, { recursive: true });

const pages = [
  ['home', '/'],
  ['aanpak', '/aanpak'],
  ['diensten', '/diensten'],
  ['verhaal', '/verhaal'],
  ['contact', '/contact'],
];

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });

// desktop
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
  reducedMotion: 'reduce',
});
for (const [name, path] of pages) {
  const page = await ctx.newPage();
  await page.goto('http://localhost:4321' + path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  await page.close();
  console.log('✓ desktop', name);
}
await ctx.close();

// mobile (home + contact)
const mctx = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
  reducedMotion: 'reduce',
  isMobile: true,
});
for (const [name, path] of [['home', '/'], ['diensten', '/diensten']]) {
  const page = await mctx.newPage();
  await page.goto('http://localhost:4321' + path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/mobile-${name}.png`, fullPage: true });
  await page.close();
  console.log('✓ mobile', name);
}
await mctx.close();
await browser.close();
console.log('done');
