// Build the presentation from the files in slides/.
//
// To prepare the tools once, do these steps in this folder:
//   1. npm install --no-save playwright
//   2. npx playwright install chromium
//
// The command "node build.js" writes deck.html, deck.pdf and one preview image for each slide.
// The command "node build.js 07 12" writes only the preview images of slides 07 and 12.
//
// Each file in slides/ has one section of the class "slide". The order of the files gives the page number.
// If the variable CHROME_PATH is set, the script uses this Chromium. Otherwise it uses the Chromium of Playwright.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const dir = __dirname;
const only = process.argv.slice(2);
const files = fs.readdirSync(path.join(dir, 'slides')).filter((f) => f.endsWith('.html')).sort();

const sections = files.map((f, i) => {
  const html = fs.readFileSync(path.join(dir, 'slides', f), 'utf8');
  const pn = i === 0 ? '' : `<div class="pn">${i + 1}</div>`;
  return html.replace(/<\/section>\s*$/, `${pn}</section>`);
});

const page = `<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>KIOsk</title>
<link rel="stylesheet" href="theme.css"></head><body>
${sections.join('\n')}
</body></html>`;
fs.writeFileSync(path.join(dir, 'deck.html'), page);

(async () => {
  const b = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto('file://' + path.join(dir, 'deck.html'));
  await p.waitForLoadState('networkidle');
  await p.evaluate(() => document.fonts.ready);
  fs.mkdirSync(path.join(dir, 'preview'), { recursive: true });
  const slides = await p.$$('.slide');
  for (let i = 0; i < slides.length; i++) {
    const nn = String(i + 1).padStart(2, '0');
    if (only.length && !only.includes(nn)) continue;
    await slides[i].screenshot({ path: path.join(dir, 'preview', `${nn}.png`) });
  }
  if (!only.length) await p.pdf({ path: path.join(dir, 'deck.pdf'), width: '1920px', height: '1080px', printBackground: true });
  await b.close();
  console.log(only.length ? `preview: ${only.join(', ')}` : `deck.pdf: ${slides.length} slides`);
})();
