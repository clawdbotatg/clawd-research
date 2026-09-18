// Render index.html -> seed-sheet-12.pdf (US Letter landscape, 2 pages: front, back).
// Uses the harness's playwright-core + its cached headless Chromium; override with
//   PLAYWRIGHT_CORE=/path/to/node_modules/playwright-core  CHROMIUM=/path/to/chrome
import { createRequire } from 'node:module';
import { readdirSync, existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const pwPath = process.env.PLAYWRIGHT_CORE || resolve(HERE, '../../../tools/node_modules/playwright-core');
const { chromium } = createRequire(import.meta.url)(pwPath);

function findChromium() {
  if (process.env.CHROMIUM) return process.env.CHROMIUM;
  const cache = join(process.env.HOME, 'Library/Caches/ms-playwright');
  const shells = readdirSync(cache).filter(d => d.startsWith('chromium_headless_shell-')).sort().reverse();
  for (const d of shells)
    for (const arch of ['mac-arm64', 'mac-x64']) {
      const bin = join(cache, d, `chrome-headless-shell-${arch}`, 'chrome-headless-shell');
      if (existsSync(bin)) return bin;
    }
  return null;
}

const browser = await chromium.launch({ executablePath: findChromium() });
const page = await browser.newPage();
await page.goto(pathToFileURL(join(HERE, 'index.html')).href, { waitUntil: 'load' });
await page.pdf({ path: join(HERE, 'seed-sheet-12.pdf'), width: '11in', height: '8.5in',
                 printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
await browser.close();
console.log('wrote seed-sheet-12.pdf');
