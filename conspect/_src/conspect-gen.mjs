#!/usr/bin/env node
/**
 * PDF-генератор прототипа конспекта под iPhone 13.
 * Узкая «телефонная» страница (не A4) + крупный шрифт → читается во всю ширину экрана без зума.
 * Usage: node conspect-gen.mjs conspect.html Conspect.pdf [--screenshots]
 */
import { chromium } from 'playwright';
import { resolve, basename } from 'path';
import { existsSync, readdirSync, mkdirSync, statSync } from 'fs';
import { homedir } from 'os';

const args = process.argv.slice(2);
const doScreenshots = args.includes('--screenshots');
const [htmlFile, outputPdf] = args.filter(a => !a.startsWith('--'));
if (!htmlFile || !outputPdf) { console.error('Usage: node conspect-gen.mjs <html> <pdf> [--screenshots]'); process.exit(1); }

const htmlPath = resolve(htmlFile);
const pdfPath = resolve(outputPdf);

function findChromium() {
  const cacheDir = resolve(homedir(), 'Library/Caches/ms-playwright');
  if (!existsSync(cacheDir)) return undefined;
  const dirs = readdirSync(cacheDir).filter(d => d.startsWith('chromium-')).sort().reverse();
  for (const dir of dirs) {
    const exe = resolve(cacheDir, dir, 'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing');
    if (existsSync(exe)) return exe;
    const exe2 = resolve(cacheDir, dir, 'chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing');
    if (existsSync(exe2)) return exe2;
  }
  return undefined;
}

const execPath = findChromium();
const browser = await chromium.launch(execPath ? { executablePath: execPath } : {});
const page = await browser.newPage();
await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle' });
await page.evaluate(async () => {
  const imgs = document.querySelectorAll('img');
  await Promise.all(Array.from(imgs).map(img => img.complete ? Promise.resolve()
    : new Promise(r => { img.onload = r; img.onerror = r; setTimeout(r, 5000); })));
});
await page.waitForTimeout(200);

await page.pdf({
  path: pdfPath,
  // Соотношение сторон = экран iPhone 13 (390×844 pt, aspect 2.164), чтобы встроенный
  // вьюер Telegram вписывал страницу почти 1:1 (не сжимал по высоте) → 1 карточка ≈ 1 экран,
  // а верхнее поле точно уводит контент из-под выреза камеры. H = 420 × 844/390 = 909.
  width: '420px',
  height: '909px',
  printBackground: true,
  preferCSSPageSize: false,
  displayHeaderFooter: false,
  margin: { top: '100px', bottom: '48px', left: '18px', right: '18px' },
});

console.log(`PDF: ${pdfPath} (${(statSync(pdfPath).size / 1024).toFixed(0)}KB)`);

if (doScreenshots) {
  const pagesDir = resolve('.', 'pages');
  mkdirSync(pagesDir, { recursive: true });
  const { execSync } = await import('child_process');
  try {
    execSync(`pdftoppm -png -r 150 "${pdfPath}" "${resolve(pagesDir, 'page')}"`, { stdio: 'pipe' });
    const n = readdirSync(pagesDir).filter(f => f.endsWith('.png')).length;
    console.log(`Screenshots: ${n} pages → ${pagesDir}/`);
  } catch { console.warn('pdftoppm missing'); }
}
await browser.close();
console.log('Done.');
